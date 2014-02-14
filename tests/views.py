from drf_toolbox import viewsets
from rest_framework.decorators import link
from tests import models as test_models, serializers as test_serializers


class ExplicitAPIEndpointsViewSet(viewsets.ModelViewSet):
    model = test_models.ExplicitAPIEndpointsModel


class NormalViewSet(viewsets.ModelViewSet):
    model = test_models.NormalModel
    serializer_class = test_serializers.NormalSerializer


class ChildViewSet(viewsets.ModelViewSet):
    model = test_models.ChildModel
    serializer_class = test_serializers.ChildSerializer


class ChildViewSetIII(viewsets.ModelViewSet):
    model = test_models.ChildModel
    serializer_class = test_serializers.ChildSerializerIII


class GrandchildViewSet(viewsets.ModelViewSet):
    model = test_models.GrandchildModel


class RelatedViewSet(viewsets.ModelViewSet):
    model = test_models.RelatedModel
    serializer_class = test_serializers.ReverseSerializer
