import argparse

from instagram_publisher.config import Settings
from instagram_publisher.instagram_client import InstagramClient


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publica midia no Instagram"
    )
    parser.add_argument(
        "--media-type",
        choices=("IMAGE", "CAROUSEL", "REELS"),
        default="IMAGE",
    )
    parser.add_argument("--image-url")
    parser.add_argument("--media-url", action="append", default=[])
    parser.add_argument("--cover-url")
    parser.add_argument("--caption", default="")
    args = parser.parse_args()

    settings = Settings.load()
    client = InstagramClient(settings)

    if args.media_type == "IMAGE":
        if not args.image_url:
            parser.error("--image-url e obrigatorio para IMAGE")
        media_id = client.publish_image(
            image_url=args.image_url,
            caption=args.caption,
        )
    elif args.media_type == "CAROUSEL":
        if len(args.media_url) < 2:
            parser.error("--media-url exige pelo menos dois itens")
        media_id = client.publish_carousel(
            item_urls=args.media_url,
            caption=args.caption,
        )
    else:
        if len(args.media_url) != 1:
            parser.error("--media-url exige exatamente um video")
        media_id = client.publish_reel(
            video_url=args.media_url[0],
            caption=args.caption,
            cover_url=args.cover_url,
        )

    print(f"Publicado com sucesso. Media ID: {media_id}")


if __name__ == "__main__":
    main()
