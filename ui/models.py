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


class MediaItem(models.Model):
    key_name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(upload_to='uploads/')
    comment = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.comment or "No comment"

class ResultItem(models.Model):
    key_name = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Result #{self.pk}"