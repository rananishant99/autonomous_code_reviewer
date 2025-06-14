# Generated by Django 5.2.2 on 2025-06-06 09:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('review', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pullrequest',
            name='body',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='pullrequest',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='pullrequest',
            name='html_url',
            field=models.URLField(default=''),
        ),
        migrations.AlterField(
            model_name='pullrequest',
            name='state',
            field=models.CharField(default='open', max_length=20),
        ),
        migrations.AlterField(
            model_name='pullrequest',
            name='title',
            field=models.CharField(default='', max_length=500),
        ),
        migrations.AlterField(
            model_name='pullrequest',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='pullrequest',
            name='user_login',
            field=models.CharField(default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='repository',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='repository',
            name='html_url',
            field=models.URLField(default=''),
        ),
        migrations.AlterField(
            model_name='repository',
            name='language',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='repository',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='reviewresult',
            name='file_reviews',
            field=models.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name='reviewresult',
            name='overall_review',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='reviewresult',
            name='pr_details',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='reviewresult',
            name='summary',
            field=models.TextField(default=''),
        ),
    ]
