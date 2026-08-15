import replicate
import os

os.environ.setdefault("REPLICATE_API_TOKEN", os.getenv("REPLICATE_API_TOKEN", ""))


def generate_ad_image(product_name: str, style: str = "lifestyle product photography") -> str:
    """Generate a marketing image with FLUX 1.1 Pro. Returns image URL."""
    output = replicate.run(
        "black-forest-labs/flux-1.1-pro",
        input={
            "prompt": f"Professional {style} of {product_name}, clean white background, studio lighting, e-commerce ready, high quality product photo",
            "aspect_ratio": "1:1",
            "output_quality": 90,
        },
    )
    return output if isinstance(output, str) else str(output)


def generate_product_video(product_name: str, image_url: str) -> str:
    """Generate a 5-second product showcase video with Kling. Returns video URL."""
    output = replicate.run(
        "kwaivgi/kling-v2.0-master",
        input={
            "prompt": f"Slow rotating product showcase of {product_name}, studio lighting, white background, professional commercial",
            "image": image_url,
            "duration": 5,
        },
    )
    return output if isinstance(output, str) else str(output)
