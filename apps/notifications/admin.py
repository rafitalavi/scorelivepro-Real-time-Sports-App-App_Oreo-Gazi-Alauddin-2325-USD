from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.contrib.auth import get_user_model
from .models import NotificationLog ,UserDevice

User = get_user_model()


def clear_all_logs(modeladmin, request, queryset):
    """Admin action: wipes the ENTIRE NotificationLog table, ignoring the selection."""
    total, _ = NotificationLog.objects.all().delete()
    modeladmin.message_user(
        request,
        f"✅ Successfully deleted all {total} notification logs.",
        messages.SUCCESS
    )
clear_all_logs.short_description = "🗑️ Clear ALL notification logs (entire table)"


class TopicTypeFilter(admin.SimpleListFilter):
    title = 'Audience Type'
    parameter_name = 'topic_type'

    def lookups(self, request, model_admin):
        return (
            ('league', '🏆 Leagues'),
            ('team', '⚽ Teams'),
            ('match', '🏟️ Matches'),
            ('global', '🌍 Global'),
            ('user', '👤 Users'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'league':
            return queryset.filter(topic__startswith='league_')
        if self.value() == 'team':
            return queryset.filter(topic__startswith='team_')
        if self.value() == 'match':
            return queryset.filter(topic__startswith='match_')
        if self.value() == 'user':
            return queryset.filter(topic__startswith='user_')
        if self.value() == 'global':
            return queryset.filter(topic='global')
        return queryset

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('get_target_audience', 'title', 'event_type', 'status_badge', 'response_info', 'created_at')
    list_display_links = ('title', 'created_at')
    list_filter = (TopicTypeFilter, 'status', 'event_type', 'created_at')
    search_fields = ('topic', 'title', 'body', 'error_message')
    list_per_page = 50
    readonly_fields = ('created_at',)
    actions = [clear_all_logs]

    def status_badge(self, obj):
        if obj.status == 'SENT':
            return format_html('<span style="color: white; background: green; padding: 3px 8px; border-radius: 4px; font-weight: bold;">✅ SENT</span>')
        return format_html('<span style="color: white; background: red; padding: 3px 8px; border-radius: 4px; font-weight: bold;">❌ FAILED</span>')
    status_badge.short_description = "Delivery Status"

    def get_target_audience(self, obj):
        """Intelligently decodes the topic into a clickable, perfectly filtered format."""
        base_url = f"?topic={obj.topic}"
        
        if obj.topic.startswith('user_'):
            try:
                user_id = int(obj.topic.split('_')[1])
                user = User.objects.get(id=user_id)
                display = f"👤 {user.email}"
            except Exception:
                display = f"👤 User #{obj.topic.split('_')[1]}"
        elif obj.topic.startswith('team_'):
            display = f"⚽ Team #{obj.topic.split('_')[1]}"
        elif obj.topic.startswith('league_'):
            display = f"🏆 League #{obj.topic.split('_')[1]}"
        elif obj.topic.startswith('match_'):
            display = f"🏟️ Match #{obj.topic.split('_')[1]}"
        elif obj.topic == 'global':
            display = "🌍 EVERYONE (Global)"
        else:
            display = str(obj.topic)
            
        return format_html('<a href="{}" style="font-weight:bold; color:#5b80b2; text-decoration:none;">{}</a>', base_url, display)
    get_target_audience.short_description = "Target Audience"

    def response_info(self, obj):
        """Displays the error message or the success Message ID from Firebase"""
        if not obj.error_message:
            return "-"
        if obj.status == 'SENT':
            return format_html('<span style="color: green; font-size: 11px;">ID: {}</span>', obj.error_message)
        errmsg = obj.error_message[:70] + "..." if len(obj.error_message) > 70 else obj.error_message
        return format_html('<span style="color: darkred; font-size: 11px;">{}</span>', errmsg)
    response_info.short_description = "Firebase API Response"



@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'guest_id', 'type', 'registration_id', 'active', 'last_updated')
    list_filter = ('type', 'active')
    search_fields = ('registration_id', 'user__email', 'guest_id')
    readonly_fields = ('last_updated', 'created_at')