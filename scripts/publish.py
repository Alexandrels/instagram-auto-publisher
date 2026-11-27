import argparse

from instagram_publisher.config import Settings
from instagram_publisher.instagram_client import InstagramClient


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publica uma imagem no feed do Instagram"
    )
    parser.add_argument("--image-url", required=True)
    parser.add_argument("--caption", default="")
    args = parser.parse_args()

    settings = Settings.load()
    client = InstagramClient(settings)
    media_id = client.publish_image(
        image_url=args.image_url,
        caption=args.caption,
    )
    print(f"Publicado com sucesso. Media ID: {media_id}")


if __name__ == "__main__":
    main()
