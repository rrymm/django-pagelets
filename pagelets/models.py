# -*- coding: utf-8 -*-
from django.db import models, transaction
from django.template import loader, Context
from django.template import Template as DjangoTemplate
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.template import compile_string, TemplateSyntaxError, StringOrigin
from django.template.context import Context

from caktus.django.db.util import slugify_uniquely

from datetime import datetime


class PageletBase(models.Model):
    creation_date = models.DateTimeField(
        _('creation date'), 
        auto_now_add=True, 
        editable=False,
    )
    created_by = models.ForeignKey(
        User, 
        related_name='pagelets_created', 
        editable=False,
    )
    
    last_changed = models.DateTimeField(
        _('last changed'), 
        auto_now=True, 
        editable=False,
    )
    modified_by = models.ForeignKey(
        User, 
        related_name='pagelets_last_modified', 
        editable=False,
    )

    def save(self, **kwargs):
        if not self.id:
            self.creation_date = datetime.now()
            
        queryset = PageletBase.objects.all()
        if self.id:
            queryset = queryset.exclude(pk=self.id)
        
        self.last_changed = datetime.now()
        
        super(PageletBase, self).save(**kwargs)


class Page(PageletBase):
    title = models.CharField(_('title'), max_length=255)
    slug = models.CharField(_('slug'), unique=True, max_length=255)
    
    def get_absolute_url(self):
    	return reverse('view_page', kwargs={'page_slug': self.slug})
    
    class Meta:
        ordering = ('title',)
    
    def __unicode__(self):
        return self.title
    
    
class Pagelet(PageletBase):
    """
    Primary model for storing pieces of static content in the database.
    """
    
    CONTENT_TYPES = (
        ('html', 'HTML'),
    #    ('mediawiki', 'MediaWiki'),
        ('markdown', 'Markdown'),
    #    ('tinymce', 'TinyMCE'),
    #    ('wymeditor', 'WYMeditor'),
        ('textile', 'Textile'),
    )
    ORDER_CHOICES = [(x, x) for x in range(-10, 11)]
    
    page = models.ForeignKey(
        Page, 
        related_name='pagelets', 
        null=True, 
        blank=True,
    )
    # whenever you need to reference a pagelet in CSS, use its slug
    slug = models.CharField(
        _('slug'),
        max_length=255,
        null=True, 
        blank=True,
    #    unique=True,
    )
    css_classes = models.CharField(
        _('CSS classes'),
        max_length=255,
        blank=True,
    )
    order = models.SmallIntegerField(
        null=True,
        blank=True,
        choices=ORDER_CHOICES,
    )
    type = models.CharField(
        _('content type'), 
        max_length=32, 
        choices=CONTENT_TYPES, 
        default='html',
    )
    content = models.TextField(_('content'), blank=True)

    def render(self, context):
        #pagelets can automagically use pagelets templatetags in order to remove boilerplate
        loaded_cms = "{% load pagelets %}\n" + self.content
        """
        skip the first portions of render_to_string() ( finding the template )
         and go directly to compiling the template/pagelet
        render_to_string abbreviated: 
                def render_to_string(template_name, dictionary=None, context_instance=None):
                       t = select/get_template(template_name)
                               template = get_template_from_string(source, origin, template_name)
                                       return Template(source, origin, name)
                       t.render(context_instance)
        
        """
        #XXX is this what the origin should be?
        origin = StringOrigin('pagelet: %s' % self.slug)
        compiled = compile_string(loaded_cms, origin ).render( context )
        try:
            if self.type in ('html', 'tinymce', 'wymeditor'):
                html = compiled
            elif self.type == "textile":
                from textile import textile
                html = textile(str(compiled))
            elif self.type == "markdown":
                from markdown import markdown
                html = markdown(compiled)
            return html
        except TemplateSyntaxError, e:
            return 'Syntax error, %s' % e
        
        raise Exception("Unsupported template content type '%s'" % content.content_type)
    
    def save(self, **kwargs):
    	# force empty slugs to None so we don't get a DuplicateKey
        if self.slug == '':
            self.slug = None
        super(Pagelet, self).save(**kwargs)
        
    class Meta:
        ordering = ('slug',)
    
    def __unicode__(self):
    	if self.slug:
    		return self.slug
    	else:
    		return self.content[:25]
