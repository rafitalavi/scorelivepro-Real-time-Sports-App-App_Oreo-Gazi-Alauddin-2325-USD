from rest_framework import serializers
from .models import UserDevice, ScheduledNotification, NotificationLog
from django.utils.timesince import timesince

class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ['registration_id', 'type', 'active', 'language']

class ScheduledNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledNotification
        fields = ['id', 'title', 'body', 'event_type', 'scheduled_time', 'is_sent', 'created_at']
        read_only_fields = ['is_sent', 'created_at']

class NotificationLogSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = NotificationLog
        fields = ['id', 'title', 'body', 'data', 'event_type', 'created_at', 'time_ago', 'is_read']

    def get_is_read(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return False
        user = request.user
        if not hasattr(user, 'fan_profile') or not user.fan_profile.last_inbox_check:
            return False
        return obj.created_at <= user.fan_profile.last_inbox_check

    def get_time_ago(self, obj):
        return timesince(obj.created_at)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        lang = self.context.get('language', 'en')
        if lang != 'en':
            from .services import translate_notification
            t_title, t_body = translate_notification(
                representation.get('title', ''),
                representation.get('body', ''),
                representation.get('event_type', 'CUSTOM'),
                lang
            )
            representation['title'] = t_title
            representation['body'] = t_body
        return representation