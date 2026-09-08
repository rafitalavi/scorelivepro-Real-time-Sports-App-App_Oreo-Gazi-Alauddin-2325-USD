from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('sports', '0009_team_is_popular'),
    ]

    operations = [
        migrations.AddField(
            model_name='fixture',
            name='extra',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
