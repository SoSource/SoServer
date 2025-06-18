from django.contrib import admin


from accounts.models import *
from transactions.models import *
from posts.models import *
from blockchain.models import *

from django.contrib import admin
from django.db.models import ForeignKey

# from django.contrib.contenttypes.models import ContentType
# admin.site.register(ContentType)

# class AutoForeignKeyAdmin(admin.ModelAdmin):
#     search_fields = ['id']
#     def __init__(self, model, admin_site):
#         super().__init__(model, admin_site)
#         self.autocomplete_fields = [
#             field.name for field in model._meta.get_fields()
#             if isinstance(field, ForeignKey)
#         ]

def full_utc(field_name, label=None):
    def _func(obj):
        value = getattr(obj, field_name, None)
        if value is None:
            return "-"
        elif not isinstance(value, datetime.datetime):
            return value
        return value.strftime('%b %d, %Y, %H:%M:%S')
    _func.short_description = label or f"{field_name.replace('_', ' ').title()}"
    _func.admin_order_field = field_name
    return _func

class AutoForeignKeyAdmin(admin.ModelAdmin):
    search_fields = ['id']

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        # Automatically set autocomplete fields for ForeignKeys
        self.autocomplete_fields = [
            field.name for field in model._meta.get_fields()
            if isinstance(field, ForeignKey)
        ]

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        # Automatically find all DateTimeFields and format them
        datetime_fields = [
            field.name for field in self.model._meta.fields
            if field.get_internal_type() == 'DateTimeField'
        ]
        formatted_fields = [f'formatted_{field}' for field in datetime_fields]
        return fields + tuple(formatted_fields)

    def __getattr__(self, name):
        if name.startswith('formatted_'):
            field_name = name.replace('formatted_', '')

            def formatted_field(obj):
                value = getattr(obj, field_name)
                return self.format_datetime(value)

            # Set the short description for the formatted field
            formatted_field.short_description = field_name.replace('_', ' ').title()
            return formatted_field

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def format_datetime(self, value):
        if value:
            return value.strftime('%Y-%m-%d %H:%M:%S UTC')
        return '-'
    
    def has_delete_permission(self, request, obj=None):
        # Prevent all deletions by returning False
        return False

class SonetAdmin(AutoForeignKeyAdmin):
    list_display = ["Title"]
    list_display_links = []
    list_editable = []
    list_filter = []
    # readonly_fields = (full_utc('updated_on_node'),)
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = Sonet

class UserAdmin(AutoForeignKeyAdmin):
    list_display = [full_utc("display_name"), full_utc('last_login'), 'is_active', full_utc('date_joined'),'id',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    # readonly_fields = ('update_on_node',)

    # def update_on_node(self, obj):
    #     if obj.updated_on_node:
    #         return obj.updated_on_node.strftime('%Y-%m-%d %H:%M:%S')
    #     return '-'
    # update_on_node.short_description = 'updated_on_node (UTC)'

    search_fields = AutoForeignKeyAdmin.search_fields + ['display_name','id']
    class Meta:
        model = User

class UserDataAdmin(AutoForeignKeyAdmin):
    list_display = ['id',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = UserData

class UserPubKeyAdmin(AutoForeignKeyAdmin):
    list_display = ["id", full_utc('created'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = UserPubKey

class SuperSignAdmin(AutoForeignKeyAdmin):
    list_display = ["pointerId", full_utc('created'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = SuperSign

class UserNotificationAdmin(AutoForeignKeyAdmin):
    list_display = ['User_obj',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = UserNotification

class NotificationAdmin(AutoForeignKeyAdmin):
    list_display = ["Title", 'id', full_utc('created'), 'pointerId', 'validated',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['id','pointerId', 'Link', 'Title']
    class Meta:
        model = Notification

class WalletAdmin(AutoForeignKeyAdmin):
    list_display = ["id", full_utc('created'),'User_obj',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = Wallet

class UserTransactionAdmin(AutoForeignKeyAdmin):
    list_display = ["id",'token_value','ReceiverWallet_obj','SenderWallet_obj',full_utc('enact_dt'),'enacted','validated',full_utc('created'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['id','ReceiverWallet_obj','SenderWallet_obj']
    class Meta:
        model = UserTransaction

class RegionAdmin(AutoForeignKeyAdmin):
    list_display = ["Name", 'AbbrName','nameType',full_utc('created'),'id','proposed_modification',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['Name','id']
    class Meta:
        model = Region

class KeyphraseAdmin(AutoForeignKeyAdmin):
    list_display = ['id', "key", full_utc('last_occured'), full_utc('first_occured')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['key']
    class Meta:
        model = Keyphrase

class KeyphraseTrendAdmin(AutoForeignKeyAdmin):
    list_display = ["key", 'trend_score','recent_occurences','total_occurences', full_utc('last_updated'), 'Chamber']
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['key']
    class Meta:
        model = KeyphraseTrend

class GenericModelAdmin(AutoForeignKeyAdmin):
    list_display = ['type', 'func', full_utc('created'), full_utc('DateTime'),'id','pointerId',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['type', 'id', 'func']
    class Meta:
        model = GenericModel


class SprenAdmin(AutoForeignKeyAdmin):
    list_display = [full_utc('created'), 'type', full_utc("DateTime"), full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = Spren

class PostAdmin(AutoForeignKeyAdmin):
    list_display = [full_utc('DateTime'), 'pointerType', 'pointerId', 'validated', 'blockId', full_utc('created'), full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['pointerType', 'pointerId','id']
    class Meta:
        model = Post

    
    # list_display = (
    #     full_utc('my_time_field', 'Start Time'),
    #     full_utc('end_time'),  # Uses default label
    #     'other_field',
    # )

# class MyModelAdmin(admin.ModelAdmin):
#     list_display = ('time_utc', 'other_field')

#     full_utc.short_description = 'Time (UTC)'


# def full_utc(obj, field):
#     # return obj.my_time_field.strftime('%H:%M')
#         # With date and seconds
#     return obj.my_time_field.strftime('%Y-%m-%d %H:%M:%S')



# class TopPostAdmin(AutoForeignKeyAdmin):
#     list_display = [full_utc('created'), 'cycle', 'Chamber', 'country']
#     list_display_links = []
#     list_editable = []
#     list_filter = []
#     search_fields = AutoForeignKeyAdmin.search_fields + []
#     class Meta:
#         model = TopPost

# class ArchiveAdmin(AutoForeignKeyAdmin):
#     list_display = [full_utc('DateTime'), full_utc('created'), 'pointerType']
#     list_display_links = []
#     list_editable = []
#     list_filter = []
#     search_fields = AutoForeignKeyAdmin.search_fields + ['pointerType']
#     class Meta:
#         model = Archive

class UserActionAdmin(AutoForeignKeyAdmin):
    list_display = [full_utc('last_updated'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = UserAction

class UserVoteAdmin(AutoForeignKeyAdmin):
    list_display = [full_utc('created'),'User_obj']
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['User_obj']
    class Meta:
        model = UserVote

class UserSavePostAdmin(AutoForeignKeyAdmin):
    list_display = [full_utc('created'),'User_obj',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['User_obj']
    class Meta:
        model = UserSavePost

class UserFollowAdmin(AutoForeignKeyAdmin):
    list_display = [full_utc('created'),'User_obj',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = UserFollow

# admin.site.register(ContentType)

# class UpdateAdmin(admin.ModelAdmin):
#     list_display = ['name','id']
#     list_display_links = []
#     list_editable = []
#     list_filter = []
#     search_fields = ['id']
#     autocomplete_fields = ['pointerKey_content_type_field', 'foreign_obj']
#     class Meta:
#         model = Update

class UpdateAdmin(admin.ModelAdmin):
    list_display = ['pointerId', 'blockchainId', full_utc('DateTime'), 'Block_obj', 'id', 'validated', full_utc('created'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    readonly_fields = ('update_on_node','added_to_node')
    def update_on_node(self, obj):
        if obj.updated_on_node:
            return obj.updated_on_node.strftime('%Y-%m-%d %H:%M:%S')
        return '-'
    update_on_node.short_description = 'updated_on_node (UTC)'
    def added_to_node(self, obj):
        if obj.added:
            return obj.added.strftime('%Y-%m-%d %H:%M:%S')
        return '-'
    added_to_node.short_description = 'added (UTC)'

    def has_delete_permission(self, request, obj=None):
        # Prevent all deletions by returning False
        return False
    search_fields = ['pointerId', 'id']
    autocomplete_fields = ['Region_obj']
    class Meta:
        model = Update


class PluginAdmin(AutoForeignKeyAdmin):
    list_display = ['id', 'Title','User_obj',full_utc('created'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = Plugin

class DataPacketAdmin(AutoForeignKeyAdmin):
    list_display = ['id', 'Node_obj','chainName', 'func',full_utc('created'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['chainName']
    class Meta:
        model = DataPacket

class NodeAdmin(AutoForeignKeyAdmin):
    list_display = ['id','node_name','User_obj',full_utc('activated_dt'),full_utc('suspended_dt'),full_utc('last_updated'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['id','node_name','User_obj']
    class Meta:
        model = Node

class NodeReviewAdmin(AutoForeignKeyAdmin):
    list_display = ['id', 'CreatorNode_obj', 'TargetNode_obj']
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + []
    class Meta:
        model = NodeReview

class ValidatorAdmin(AutoForeignKeyAdmin):
    list_display = ['id', full_utc('created'),'blockchainType','validatorType','func','is_valid','CreatorNode_obj',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['validatorType','func','id']
    class Meta:
        model = Validator

class BlockAdmin(AutoForeignKeyAdmin):
    list_display = ['id','Blockchain_obj','index','CreatorNode_obj',full_utc('DateTime'),'validated',full_utc('updated_on_node')]
    list_display_links = []
    list_editable = []
    list_filter = []
    ordering = ['-DateTime', '-created', '-index']
    search_fields = AutoForeignKeyAdmin.search_fields + ['blockchainType','id']
    class Meta:
        model = Block

class BlockchainAdmin(AutoForeignKeyAdmin):
    list_display = ['id', 'genesisType', 'genesisName', 'chain_length','genesisId', full_utc('data_added_datetime'),full_utc('last_block_datetime'),full_utc('created'),full_utc('updated_on_node')]
    list_display_links = []
    list_editable = ['genesisName']
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['genesisName', 'genesisId','id']
    class Meta:
        model = Blockchain

class EventLogAdmin(AutoForeignKeyAdmin):
    list_display = ['type',full_utc('created'),full_utc('updated_on_node'), 'id']
    list_display_links = []
    list_editable = []
    list_filter = []
    search_fields = AutoForeignKeyAdmin.search_fields + ['type', 'id']
    class Meta:
        model = EventLog

admin.site.register(User, UserAdmin)
admin.site.register(UserPubKey, UserPubKeyAdmin)
admin.site.register(SuperSign, SuperSignAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserAction, UserActionAdmin)
admin.site.register(UserVote, UserVoteAdmin)
admin.site.register(UserSavePost, UserSavePostAdmin)
admin.site.register(UserFollow, UserFollowAdmin)
# admin.site.register(UserAction, UserActionAdmin)
admin.site.register(UserData, UserDataAdmin)


admin.site.register(Wallet, WalletAdmin)
admin.site.register(UserTransaction, UserTransactionAdmin)

admin.site.register(Region, RegionAdmin)
admin.site.register(Keyphrase, KeyphraseAdmin)
admin.site.register(KeyphraseTrend, KeyphraseTrendAdmin)
admin.site.register(GenericModel, GenericModelAdmin)
admin.site.register(Spren, SprenAdmin)
# admin.site.register(SprenItem, SprenItemAdmin)
admin.site.register(Update, UpdateAdmin)
admin.site.register(Post, PostAdmin)
# admin.site.register(TopPost, TopPostAdmin)
# admin.site.register(Archive, ArchiveAdmin)

admin.site.register(Sonet, SonetAdmin)
admin.site.register(Plugin, PluginAdmin)
admin.site.register(DataPacket, DataPacketAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(NodeReview, NodeReviewAdmin)
admin.site.register(Validator, ValidatorAdmin)
admin.site.register(Block, BlockAdmin)
admin.site.register(Blockchain, BlockchainAdmin)
admin.site.register(EventLog, EventLogAdmin)




