from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sports', '0009_team_is_popular'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='fixture',
                    name='extra',
                    field=models.IntegerField(blank=True, null=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE sports_fixture ADD COLUMN IF NOT EXISTS extra integer;",
                    reverse_sql="ALTER TABLE sports_fixture DROP COLUMN IF EXISTS extra;",
                ),
            ],
        ),
    ]

