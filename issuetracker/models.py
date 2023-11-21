from django.db import models


class File(models.Model):
    activity = models.CharField(max_length=255, blank=True, null=True)
    actor = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=False)
    type = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True, null=True)
    creator = models.CharField(max_length=255)
    source = models.CharField(max_length=255, blank=True)
    unique_together = [["id", "source"]]


class Keyword(models.Model):
    creator = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True)
    unique_together = [["id", "source"]]


class Message(models.Model):
    id = models.IntegerField(primary_key=True)
    content = models.CharField(max_length=255, blank=True, null=True)
    creation = models.FloatField(blank=True, null=True)
    creator = models.ForeignKey(
        "User", related_name="issues_creator", on_delete=models.CASCADE
    )
    summary = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=255, blank=True)

    issue = models.ForeignKey(
        "Issue", on_delete=models.CASCADE, related_name="messages", null=True
    )

    files = models.ManyToManyField(File)

    class Meta:
        unique_together = [["id", "source"]]
        ordering = ["-creation"]


class Issue(models.Model):
    id = models.IntegerField(primary_key=True)
    activity = models.CharField(max_length=255, blank=True, null=True)
    actor = models.IntegerField(blank=True, null=True)
    assignedto = models.ForeignKey(
        "User",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="assigned_to",
    )
    creation = models.FloatField(max_length=255, blank=True)
    creator = models.ForeignKey(
        "User", blank=True, null=True, on_delete=models.CASCADE, related_name="creator"
    )
    status = models.ForeignKey(
        "Status", blank=True, null=True, on_delete=models.CASCADE, related_name="issues"
    )
    priority = models.ForeignKey(
        "Priority",
        blank=True,
        related_name="issues",
        null=True,
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=255, blank=True)

    latest_activity = models.FloatField(max_length=255)

    keywords = models.ManyToManyField(Keyword)

    files = models.ManyToManyField(File)

    class Meta:
        unique_together = [["id", "source"]]


class Priority(models.Model):
    id = models.IntegerField(primary_key=True)
    creator = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = (("id", "source"),)


class Status(models.Model):
    id = models.IntegerField(primary_key=True)
    creator = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = (("id", "source"),)


class User(models.Model):
    creation = (models.FloatField(),)
    realname = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    organisation = models.CharField(max_length=255, null=True)
    email = models.CharField(max_length=255, null=True, blank=True)
