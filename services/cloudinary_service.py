import os
import cloudinary
import cloudinary.uploader
from django.conf import settings

# Configure Cloudinary using environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

class CloudinaryService:
    """
    Service class to interact with Cloudinary API directly.
    """
    
    @staticmethod
    def upload_image(file, folder="vendor_nest"):
        """
        Uploads an image file to Cloudinary.
        Returns a dictionary with public_id, url, and success status.
        """
        try:
            result = cloudinary.uploader.upload(file, folder=folder)
            return {
                "public_id": result.get("public_id"),
                "url": result.get("secure_url"),
                "success": True
            }
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }

    @staticmethod
    def delete_image(public_id):
        """
        Deletes an image from Cloudinary using its public ID.
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            return False
