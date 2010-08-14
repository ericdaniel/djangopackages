import logging 
import os
import re
from urllib import urlopen

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models 
from django.utils.translation import ugettext_lazy as _ 

from github2.client import Github
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField 

logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s "%(message)s" in %(funcName)s() line %(lineno)d in %(pathname)s', 
        filename='database.log',
        filemode='a',
)

downloads_re = re.compile(r'<td style="text-align: right;">[0-9]{1,}</td>')

class BaseModel(models.Model): 
    """ Base abstract base class to give creation and modified times """
    created     = CreationDateTimeField(_('created'))
    modified    = ModificationDateTimeField(_('modified'))

    class Meta: 
        abstract = True 

class Category(BaseModel):

    title = models.CharField(_("Title"), max_length="50")
    description = models.TextField(_("Participants"), blank=True)

    class Meta:
        ordering = ['title']

    def __unicode__(self):
        return self.title

REPO_CHOICES = (
    ('http://github.com', 'Github',),
    #('bitbucket', 'bitbucket',),
    #('code.google.com', 'code.google.com', ),
)

class Package(BaseModel):
    
    title           = models.CharField(_("Title"), max_length="100")
    slug            = models.SlugField(_("Slug"))
    category        = models.ForeignKey(Category)
    repo            = models.CharField(_("Repo"), max_length="50", choices=REPO_CHOICES)
    repo_description= models.TextField(_("Repo Description"), blank=True)
    repo_url        = models.URLField(_("repo URL"))
    repo_watchers   = models.IntegerField(_("repo watchers"), default=0)
    repo_forks      = models.IntegerField(_("repo forks"), default=0)
    pypi_url        = models.URLField(_("pypi URL"), blank=True)
    pypi_version    = models.CharField(_("Current Pypi version"), max_length="20", blank=True)    
    pypi_downloads  = models.IntegerField(_("Pypi downloads"), default=0)
    related_packages    = models.ManyToManyField("self", blank=True)
    participants    = models.TextField(_("Participants"), 
                        help_text="List of collaborats/participants on the project", blank=True)
                        
    def participant_list(self):
        
        return self.participants.split(',')
    
    def save(self, *args, **kwargs):
        
        # Get the downloads from pypi
        # TODO - handle when version is added or not
        if self.pypi_url:
            page = urlopen(self.pypi_url)
            page = page.read()
            match = downloads_re.search(page).group()
            if match:
                self.pypi_downloads = match.replace('<td style="text-align: right;">', '')
                self.pypi_downloads = self.pypi_downloads.replace('</td>', '')
                self.pypi_downloads = int(self.pypi_downloads)
            else:
                self.pypi_downloads = 0
            
        # Get the repo watchers number
        # TODO - make this abstracted so we can plug in other repos
        github   = Github()
        repo_name    = self.repo_url.replace('http://github.com/','')
        repo         = github.repos.show(repo_name)
        self.repo_watchers    = repo.watchers # set watchers
        self.repo_forks       = repo.forks # set fork
        self.repo_description = repo.description


        collaborators = github.repos.list_collaborators(repo_name)
        if collaborators:
            self.participants = ','.join(collaborators)
        
        super(Package, self).save(*args, **kwargs) # Call the "real" save() method.
        
        # get committers

    class Meta:
        ordering = ['title']    
                    
    def __unicode__(self):
        
        return self.title
    
class PackageExample(BaseModel):
    
    package      = models.ForeignKey(Package)
    title        = models.CharField(_("Title"), max_length="100")
    url          = models.URLField(_("Repo URL"))
    active       = models.BooleanField(_("Active"), default=False, help_text="Moderators have to approve links before they are provided")
    
    class Meta:
        ordering = ['title']    

    def __unicode__(self):    
        return self.title