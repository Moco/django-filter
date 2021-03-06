from datetime import datetime, timedelta

from django import forms
from django.db.models import Q
from django.db.models.sql.constants import QUERY_TERMS
from django.utils.translation import ugettext_lazy as _

from django_filters.fields import RangeField, LookupTypeField, RealDateRangeField

__all__ = [
    'Filter', 'CharFilter', 'BooleanFilter', 'ChoiceFilter',
    'MultipleChoiceFilter', 'DateFilter', 'DateTimeFilter', 'TimeFilter',
    'ModelChoiceFilter', 'ModelMultipleChoiceFilter', 'NumberFilter',
    'RangeFilter', 'DateRangeFilter', 'AllValuesFilter', 
    'RealDateRangeFilter', 'VisitRangeFilter', 'GroupFilter',
]

LOOKUP_TYPES = sorted(QUERY_TERMS.keys())

class Filter(object):
    creation_counter = 0
    field_class = forms.Field

    def __init__(self, name=None, label=None, widget=None, action=None,
        lookup_type='exact', required=False, **kwargs):
        self.name = name
        self.label = label
        if action:
            self.filter = action
        self.lookup_type = lookup_type
        self.widget = widget
        self.required = required
        self.extra = kwargs

        self.creation_counter = Filter.creation_counter
        Filter.creation_counter += 1

    @property
    def field(self):
        if not hasattr(self, '_field'):
            if self.lookup_type is None or isinstance(self.lookup_type, (list, tuple)):
                if self.lookup_type is None:
                    lookup = [(x, x) for x in LOOKUP_TYPES]
                else:
                    lookup = [(x, x) for x in LOOKUP_TYPES if x in self.lookup_type]
                self._field = LookupTypeField(self.field_class(
                    required=self.required, widget=self.widget, **self.extra),
                    lookup, required=self.required, label=self.label)
            else:
                self._field = self.field_class(required=self.required,
                    label=self.label, widget=self.widget, **self.extra)
        return self._field

    def filter(self, qs, value):
        if not value:
            return qs
        if isinstance(value, (list, tuple)):
            lookup = str(value[1])
            if not lookup:
                lookup = 'exact' # we fallback to exact if no choice for lookup is provided
            value = value[0]
        else:
            lookup = self.lookup_type
        if value:
            return qs.filter(**{'%s__%s' % (self.name, lookup): value})
        return qs

class CharFilter(Filter):
    field_class = forms.CharField

class BooleanFilter(Filter):
    field_class = forms.NullBooleanField

    def filter(self, qs, value):
        if value is not None:
            return qs.filter(**{self.name: value})
        return qs

class ChoiceFilter(Filter):
    field_class = forms.ChoiceField

class MultipleChoiceFilter(Filter):
    """
    This filter preforms an OR query on the selected options.
    """
    field_class = forms.MultipleChoiceField

    def filter(self, qs, value):
        value = value or ()
        # TODO: this is a bit of a hack, but ModelChoiceIterator doesn't have a
        # __len__ method
        if len(value) == len(list(self.field.choices)):
            return qs
        q = Q()
        for v in value:
            q |= Q(**{self.name: v})
        return qs.filter(q).distinct()

class DateFilter(Filter):
    field_class = forms.DateField

    def filter(self, qs, value):
        if value:
            return qs.filter(**{
                '%s__year'%self.name:value.year, 
                '%s__month'%self.name:value.month, 
                '%s__day'%self.name:value.day})
        return qs

class RealDateRangeFilter(Filter):
    field_class = RealDateRangeField

    def filter(self, qs, value):
        if value:
            return qs.filter(**{'%s__range' % self.name: (value.start, value.stop+timedelta(1))})
        return qs

class VisitRangeFilter(Filter):
    field_class = RealDateRangeField
    
    def filter(self, qs, value):
        if value:
            return qs.filter(**{'member__transactions__created__range': (value.start, value.stop+timedelta(1))})
        return qs

class GroupFilter(Filter):
    field_class = forms.MultipleChoiceField

    def filter(self, qs, value):
        value = value or ()
        # TODO: this is a bit of a hack, but ModelChoiceIterator doesn't have a
        # __len__ method
        if len(value) == len(list(self.field.choices)):
            return qs
        q = Q()
        for v in value:
            q |= Q(**{'member__intel_group_memberships__group': v})
        return qs.filter(q).distinct()


class DateTimeFilter(Filter):
    field_class = forms.DateTimeField

class TimeFilter(Filter):
    field_class = forms.TimeField

class ModelChoiceFilter(Filter):
    field_class = forms.ModelChoiceField

class ModelMultipleChoiceFilter(MultipleChoiceFilter):
    field_class = forms.ModelMultipleChoiceField

class NumberFilter(Filter):
    field_class = forms.DecimalField

class RangeFilter(Filter):
    field_class = RangeField

    def filter(self, qs, value):
        if value:
            return qs.filter(**{'%s__range' % self.name: (value.start, value.stop)})
        return qs

class DateRangeFilter(ChoiceFilter):
    options = {
        '': (_('Any Date'), lambda qs, name: qs.all()),
        1: (_('Today'), lambda qs, name: qs.filter(**{
            '%s__year' % name: datetime.today().year,
            '%s__month' % name: datetime.today().month,
            '%s__day' % name: datetime.today().day
        })),
        2: (_('Past 7 days'), lambda qs, name: qs.filter(**{
            '%s__gte' % name: (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d'),
            '%s__lt' % name: (datetime.today()+timedelta(days=1)).strftime('%Y-%m-%d'),
        })),
        3: (_('This month'), lambda qs, name: qs.filter(**{
            '%s__year' % name: datetime.today().year,
            '%s__month' % name: datetime.today().month
        })),
        4: (_('This year'), lambda qs, name: qs.filter(**{
            '%s__year' % name: datetime.today().year,
        })),
    }

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = [(key, value[0]) for key, value in self.options.iteritems()]
        super(DateRangeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = ''
        return self.options[value][1](qs, self.name)

class AllValuesFilter(ChoiceFilter):
    @property
    def field(self):
        qs = self.model._default_manager.distinct().order_by(self.name).values_list(self.name, flat=True)
        self.extra['choices'] = [(o, o) for o in qs]
        return super(AllValuesFilter, self).field
