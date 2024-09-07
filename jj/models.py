from django.db import models
from django.contrib.auth.models import User

class Session(models.Model):
    name = models.CharField(max_length=255, blank=True, default='')
    resolution = models.CharField(max_length=255, blank=True, default='')
    details = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    aff_speaker1 = models.CharField(max_length=255, blank=True, default='')
    aff_speaker2 = models.CharField(max_length=255, blank=True, default='')
    con_speaker1 = models.CharField(max_length=255, blank=True, default='')
    con_speaker2 = models.CharField(max_length=255, blank=True, default='')
    
    constructive1 = models.TextField(blank=True, default='')
    constructive2 = models.TextField(blank=True, default='')
    crossfire1 = models.TextField(blank=True, default='')
    rebuttal1 = models.TextField(blank=True, default='')
    rebuttal2 = models.TextField(blank=True, default='')
    crossfire2 = models.TextField(blank=True, default='')
    summary1 = models.TextField(blank=True, default='')
    summary2 = models.TextField(blank=True, default='')
    grand_crossfire = models.TextField(blank=True, default='')
    final_focus1 = models.TextField(blank=True, default='')
    final_focus2 = models.TextField(blank=True, default='')
    
    response = models.TextField(blank=True, default='')
    
    def __str__(self):
        return self.name