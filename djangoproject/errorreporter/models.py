from django.db import models


# Create your models here.
class CrashReport(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.CharField(max_length=200, unique=True)
    sysinfo = models.TextField()
    comments = models.CharField(max_length=300)
    stack = models.TextField(db_index=True)
    version = models.CharField(max_length=10, db_index=True)
    date = models.DateField(db_index=True)
    os = models.CharField(max_length=50, db_index=True)
    machine = models.CharField(max_length=50, db_index=True)

    def __unicode__(self):  # Python 3: def __str__(self):
        return "%s: Version %s\n %s\n %s\n" % (self.timestamp, self.version, self.stack, self.comments)
