import cloudinary
from graphene import Scalar

class CloudinaryScalar(Scalar):
    @staticmethod
    def serialize(obj):
        if isinstance(obj, cloudinary.models.CloudinaryField):
            return obj.url
        return str(obj)

    @staticmethod
    def parse_literal(node):
        if isinstance(node, str):
            return cloudinary.CloudinaryField(url=node)
        return node
    
    @staticmethod
    def serialize(cloudinary_field):
        return cloudinary_field.url if cloudinary_field else None

    @staticmethod
    def parse_literal(node):
        return node.value

    @staticmethod
    def parse_value(value):
        return value