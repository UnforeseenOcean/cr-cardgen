#!/usr/bin/env python3

import json
import logging
import os
import shutil
import sys

import pngquant
import requests
import yaml
from PIL import Image
from PIL import ImageCms

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CONFIG = os.path.join("config.yaml")


def load_json(filename):
    """Load json by filename."""
    with open(filename, encoding='utf-8', mode='r') as f:
        data = json.load(f)
    return data


def get_cards_data(config, local=False):
    if local:
        cards_data = load_json(config["cards_data"])
    else:
        r = requests.get(config["cards_data_url"])
        cards_data = r.json()

    # Add promo data
    # cards_data.extend([
    #     {
    #         "key": "shelly",
    #         "name": "Shelly",
    #         "elixir": 4,
    #         "type": "Troop",
    #         "rarity": "Epic",
    #         "arena": 1,
    #         "description": "He deals BIG damage up close - not so much at range. What he lacks in accuracy, he makes up for with his impressively bushy eyebrows.",
    #         "id": 26000044
    #     },
    #     {
    #         "key": "bo",
    #         "name": "Bo",
    #         "elixir": 4,
    #         "type": "Troop",
    #         "rarity": "Legendary",
    #         "arena": 10,
    #         "description": "Not quite a Wizard, nor an Archer - he shoots a magic arrow that passes through and damages all enemies in its path. It's not a trick, it's magic!",
    #         "id": 26000062
    #     },
    # ])

    return cards_data


def makedirs(dirs):
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)


def generate_cards(is_gold=False):
    """Generate Clash Royale cards."""
    with open(CONFIG) as f:
        config = yaml.load(f)

    cards_data = get_cards_data(config, local=True)

    src_path = config["src_dir"]
    spells_path = config["spells_dir"]
    if is_gold:
        output_png24_dir = config["output_png24_gold_dir"]
        output_png8_dir = config["output_png8_gold_dir"]
    else:
        output_png24_dir = config["output_png24_dir"]
        output_png8_dir = config["output_png8_dir"]

    makedirs([output_png8_dir, output_png24_dir])

    filenames = dict((v, k) for k, v in config["cards"].items())

    if is_gold:
        card_frame = Image.open(os.path.join(src_path, "frame-card-gold.png"))
        leggie_frame = Image.open(os.path.join(src_path, "frame-legendary-gold.png"))
    else:
        card_frame = Image.open(os.path.join(src_path, "frame-card.png"))
        leggie_frame = Image.open(os.path.join(src_path, "frame-legendary.png"))

    card_mask = Image.open(
        os.path.join(src_path, "mask-card.png")).convert("RGBA")
    leggie_mask = Image.open(
        os.path.join(src_path, "mask-legendary.png")).convert("RGBA")

    commons_bg = Image.open(os.path.join(src_path, "bg-commons.png"))
    rare_bg = Image.open(os.path.join(src_path, "bg-rare.png"))
    epic_bg = Image.open(os.path.join(src_path, "bg-epic.png"))
    leggie_bg = Image.open(os.path.join(src_path, "bg-legendary.png"))
    leggie_gold_bg = Image.open(os.path.join(src_path, "bg-legendary-gold.png"))
    gold_bg = Image.open(os.path.join(src_path, "bg-gold.png"))

    size = card_frame.size

    for card_data in cards_data:
        name = card_data['key']
        rarity = card_data['rarity']

        filename = filenames.get(name)

        if filename is None:
            logger.warning(f"{name} does not have a corresponding file, continuing…")
            continue

        card_src = os.path.join(spells_path, "{}.png".format(filename))
        card_dst_png24 = os.path.join(output_png24_dir, "{}.png".format(name))
        card_dst_png8 = os.path.join(output_png8_dir, "{}.png".format(name))
        card_image = Image.open(card_src)

        # scale card to fit frame
        scale = 1
        card_image = card_image.resize(
            [int(dim * scale) for dim in card_image.size])

        # pad card with transparent pixels to be same size as output
        card_size = card_image.size
        card_x = int((size[0] - card_size[0]) / 2)
        card_y = int((size[1] - card_size[1]) / 2)
        card_x1 = card_x + card_size[0]
        card_y1 = card_y + card_size[1]

        im = Image.new("RGBA", size)
        im.paste(
            card_image, (card_x, card_y, card_x1, card_y1))
        card_image = im

        im = Image.new("RGBA", size)

        if rarity == "Legendary":
            im.paste(card_image, mask=leggie_mask)
        else:
            im.paste(card_image, mask=card_mask)

        card_image = im

        im = Image.new("RGBA", size)
        im = Image.alpha_composite(im, card_image)

        # use background image for regular cards
        bg = None
        if is_gold:
            if rarity == 'Legendary':
                bg = leggie_gold_bg
            else:
                bg = gold_bg
        elif rarity == "Commons":
            bg = commons_bg
        elif rarity == "Rare":
            bg = rare_bg
        elif rarity == "Epic":
            bg = epic_bg
        elif rarity == "Legendary":
            bg = leggie_bg
        else:
            bg = Image.new("RGBA", size)

        # add frame
        im = Image.alpha_composite(bg, im)
        if rarity == "Legendary":
            im = Image.alpha_composite(im, leggie_frame)
        else:
            im = Image.alpha_composite(im, card_frame)

        # save and output path to std out

        converted_im = ImageCms.profileToProfile(im, './AdobeRGB1998.icc', 'sRGB.icc')
        converted_im.save(card_dst_png24)
        logger.info(card_dst_png24)


def create_size(w, h, folder_name, is_gold=False):
    with open(CONFIG) as f:
        config = yaml.load(f)

    root = config.get('working_dir')

    if is_gold:
        src_dir = config.get('output_png24_gold_dir')
    else:
        src_dir = config.get('output_png24_dir')

    dst_dir = os.path.join(root, folder_name)

    os.makedirs(dst_dir, exist_ok=True)

    cards_data = get_cards_data(config, local=True)

    for card_data in cards_data:
        key = card_data.get('key')
        card_src = os.path.join(src_dir, "{}.png".format(key))
        card_dst = os.path.join(dst_dir, "{}.png".format(key))

        try:
            im = Image.open(card_src)
            im.thumbnail((w, h), Image.ANTIALIAS)
            im.save(card_dst)
            logger.info(card_dst)
        except IOError:
            logger.error(f"Cannot create thumbnail for {key}")


def create_png8(folder_name, is_gold=False):
    with open(CONFIG) as f:
        config = yaml.load(f)

    root = config.get('working_dir')

    if is_gold:
        src_dir = config.get('output_png24_gold_dir')
    else:
        src_dir = config.get('output_png24_dir')

    dst_dir = os.path.join(root, folder_name)

    os.makedirs(dst_dir, exist_ok=True)

    cards_data = get_cards_data(config, local=True)

    for card_data in cards_data:
        key = card_data.get('key')
        card_src = os.path.join(src_dir, "{}.png".format(key))
        card_dst = os.path.join(dst_dir, "{}.png".format(key))

        try:
            pngquant.quant_image(
                image=card_src,
                dst=card_dst
            )
            logger.info(card_dst)
        except IOError:
            logger.error(f"Cannot create thumbnail for {key}")


def copyfiles():
    """Copy card images to cr-api-web."""
    with open(CONFIG) as f:
        config = yaml.load(f)

    src_root = '/Users/sml/Dropbox/git/cr-cardgen/cardgen'
    dst_root = '/Users/sml/Dropbox/git/cr-api-web/public/static/img'

    folders = [
        dict(
            src='./cards',
            dst='./cards'
        ),
        dict(
            src='./cards-75',
            dst='./cards-75'
        ),
        dict(
            src='./cards-150',
            dst='./cards-150'
        ),
        dict(
            src='./cards-gold',
            dst='./cards-gold'
        ),
        dict(
            src='./cards-75-gold',
            dst='./cards-75-gold'
        ),
        dict(
            src='./cards-150-gold',
            dst='./cards-150-gold'
        ),
    ]

    for folder in folders:
        src = os.path.join(src_root, folder.get('src'))
        dst = os.path.join(dst_root, folder.get('dst'))
        for file in os.listdir(src):
            if not file.startswith('.'):
                src_path = os.path.join(src, file)
                dst_path = os.path.join(dst, file)
                shutil.copy(src_path, dst_path)
                logger.info(dst_path)


def main(arguments):
    """Main."""

    generate_cards(is_gold=False)
    create_size(75, 90, "cards-75", is_gold=False)
    create_size(150, 180, "cards-150", is_gold=False)
    create_png8("cards-png8", is_gold=False)

    generate_cards(is_gold=True)
    create_size(75, 90, "cards-75-gold", is_gold=True)
    create_size(150, 180, "cards-150-gold", is_gold=True)
    create_png8("card-gold-png8", is_gold=True)

    copyfiles()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
