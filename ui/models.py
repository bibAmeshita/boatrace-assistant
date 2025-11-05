from django.db import models

class Program(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Character(models.Model):
    name = models.CharField(max_length=50)
    tone = models.TextField(verbose_name="口調")
    prediction = models.TextField(verbose_name="予想")
    index = models.CharField(max_length=50, verbose_name="指数", default="")

    def __str__(self):
        return self.name


class Template(models.Model):
    name = models.CharField(max_length=50)
    tag = models.CharField(max_length=50, unique=True)
    content = models.TextField(verbose_name="内容")

    def __str__(self):
        return self.name