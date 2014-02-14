from __future__ import absolute_import, unicode_literals
from drf_toolbox.compat import models, django_pgfields_installed
from tests.compat import mock


class ExplicitAPIEndpointsModel(models.Model):
    api_endpoints = models.IntegerField()
    something = models.CharField(max_length=50)

    class Meta:
        app_label = 'tests'


class NormalModel(models.Model):
    foo = models.IntegerField()
    bar = models.IntegerField()
    baz = models.IntegerField()
    bacon = models.IntegerField(unique=True)

    def get_absolute_url(self):
        return '/normal/%s/' % self.id

    class Meta:
        app_label = 'tests'
        unique_together = ('bar', 'baz')


class ChildModel(models.Model):
    normal = models.ForeignKey(NormalModel)

    class Meta:
        app_label = 'tests'


class GrandchildModel(models.Model):
    child = models.ForeignKey(ChildModel)

    class Meta:
        app_label = 'tests'


class RelatedModel(models.Model):
    baz = models.IntegerField()
    normal = models.ForeignKey(NormalModel, related_name='related_model')

    class Meta:
        app_label = 'tests'


class CreatedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'tests'


if django_pgfields_installed:
    with mock.patch.multiple(models.CompositeField,
                             create_type=mock.DEFAULT,
                             create_type_sql=mock.DEFAULT,
                             register_composite=mock.DEFAULT):
        class CoordsField(models.CompositeField):
            x = models.IntegerField()
            y = models.IntegerField()


    class PGFieldsModel(models.Model):
        id = models.UUIDField(auto_add=True, primary_key=True)
        uuid = models.UUIDField()
        array = models.ArrayField(of=models.IntegerField)
        extra = models.JSONField()
        coords = CoordsField()

        class Meta:
            app_label = 'tests'
