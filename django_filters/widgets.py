from itertools import chain
from urllib import urlencode

from django import forms
from django.db.models.fields import BLANK_CHOICE_DASH
from django.forms.widgets import flatatt
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from django.contrib.admin.widgets import AdminDateWidget


class LinkWidget(forms.Widget):
    def __init__(self, attrs=None, choices=()):
        super(LinkWidget, self).__init__(attrs)

        self.choices = choices

    def value_from_datadict(self, data, files, name):
        value = super(LinkWidget, self).value_from_datadict(data, files, name)
        self.data = data
        return value

    def render(self, name, value, attrs=None, choices=()):
        if not hasattr(self, 'data'):
            self.data = {}
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs)
        output = [u'<ul%s>' % flatatt(final_attrs)]
        options = self.render_options(choices, [value], name)
        if options:
            output.append(options)
        output.append('</ul>')
        return mark_safe(u'\n'.join(output))

    def render_options(self, choices, selected_choices, name):
        selected_choices = set(force_unicode(v) for v in selected_choices)
        output = []
        for option_value, option_label in chain(self.choices, choices):
            if isinstance(option_label, (list, tuple)):
                for option in option_label:
                    output.append(self.render_option(name, selected_choices, *option))
            else:
                output.append(self.render_option(name, selected_choices, option_value, option_label))
        return u'\n'.join(output)

    def render_option(self, name, selected_choices, option_value, option_label):
        option_value = force_unicode(option_value)
        if option_label == BLANK_CHOICE_DASH[0][1]:
            option_label = _("All")
        data = self.data.copy()
        data[name] = option_value
        selected = data == self.data or option_value in selected_choices
        try:
            url = data.urlencode()
        except AttributeError:
            url = urlencode(data)
        return self.option_string() % {
             'attrs': selected and ' class="selected"' or '',
             'query_string': url,
             'label': force_unicode(option_label)
        }

    def option_string(self):
        return '<li><a%(attrs)s href="?%(query_string)s">%(label)s</a></li>'

class RangeWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        # TODO: this is a dirty hack, and if we ever need any ranges for
        # larger values, we'll be in trouble. However, I can't find exactly
        # where this RangeWidget is init'ed, so it's hard to improve.
        if attrs:
            attrs['size'] = '3'
        else:
            attrs = {'size': '3'}
        widgets = (forms.TextInput(attrs=attrs), forms.TextInput(attrs=attrs))
        super(RangeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.start, value.stop]
        return [None, None]

    def format_output(self, rendered_widgets):
        return u'-'.join(rendered_widgets)

class RealDateRangeWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        widgets = (AdminDateWidget(attrs=attrs), AdminDateWidget(attrs=attrs))
        super(RealDateRangeWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            print "VV", value.start, value.stop
            return [value.start, value.stop]
        return [None, None]

    def format_output(self, rendered_widgets):
        return u' to '.join(rendered_widgets)

class LookupTypeWidget(forms.MultiWidget):
    def decompress(self, value):
        if value is None:
            return [None, None]
        return value
