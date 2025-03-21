from django.db import models

# Create your models here.
class Candidate(models.Model):
    sbd = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    birth = models.CharField(max_length=200)
    place = models.CharField(max_length=200)
    sex = models.CharField(max_length=200)
    class_name = models.CharField(max_length=200)
    school = models.CharField(max_length=200)
    subject = models.CharField(max_length=200)
    score = models.FloatField()
    rank = models.CharField(max_length=200)
    prize = models.CharField(max_length=200)
