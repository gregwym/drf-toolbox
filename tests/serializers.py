from drf_toolbox.compat import django_pgfields_installed
from drf_toolbox.serializers import ModelSerializer
from tests import models as test_models


class ExplicitAPIEndpointsSerializer(ModelSerializer):
    class Meta:
        model = test_models.ExplicitAPIEndpointsModel


class NormalSerializer(ModelSerializer):
    class Meta:
        model = test_models.NormalModel


class ChildSerializer(ModelSerializer):
    class Meta:
        model = test_models.ChildModel


class ChildSerializerII(ModelSerializer):
    class Meta:
        model = test_models.ChildModel
        fields = {
            'normal': ('id', 'bacon'),
        }
        exclude = {}


class ChildSerializerIII(ModelSerializer):
    class Meta:
        model = test_models.ChildModel
        exclude = ('normal',)


class ReverseSerializer(ModelSerializer):
    class Meta:
        fields = ('bar', 'baz', 'bacon', 'related_model')
        model = test_models.NormalModel


class CreatedSerializer(ModelSerializer):
    class Meta:
        fields = ('created',)
        model = test_models.CreatedModel


if django_pgfields_installed:
    class PGFieldsSerializer(ModelSerializer):
        class Meta:
            model = test_models.PGFieldsModel
