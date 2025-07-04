# Generated by Django 5.0.4 on 2025-06-06 22:38

import django.contrib.postgres.indexes
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('blockchain', '0002_initial'),
        ('posts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='datapacket',
            name='Region_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_region_obj', to='posts.region'),
        ),
        migrations.AddField(
            model_name='eventlog',
            name='Region_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_region_obj', to='posts.region'),
        ),
        migrations.AddField(
            model_name='node',
            name='User_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='eventlog',
            name='Node_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='blockchain.node'),
        ),
        migrations.AddField(
            model_name='datapacket',
            name='Node_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='blockchain.node'),
        ),
        migrations.AddField(
            model_name='block',
            name='CreatorNode_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='blockchain.node'),
        ),
        migrations.AddField(
            model_name='nodereview',
            name='CreatorNode_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='creator_node_obj', to='blockchain.node'),
        ),
        migrations.AddField(
            model_name='nodereview',
            name='TargetNode_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='target_node_obj', to='blockchain.node'),
        ),
        migrations.AddField(
            model_name='plugin',
            name='Block_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='blockchain.block'),
        ),
        migrations.AddField(
            model_name='plugin',
            name='User_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='sonet',
            name='Block_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='blockchain.block'),
        ),
        migrations.AddField(
            model_name='validator',
            name='Block_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='blockchain.block'),
        ),
        migrations.AddField(
            model_name='validator',
            name='CreatorNode_obj',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='blockchain.node'),
        ),
        migrations.AddIndex(
            model_name='block',
            index=django.contrib.postgres.indexes.GinIndex(fields=['data'], name='Block_data_has_key_index'),
        ),
        migrations.AddIndex(
            model_name='validator',
            index=django.contrib.postgres.indexes.GinIndex(fields=['data'], name='Validator_data_has_key_index'),
        ),
    ]
