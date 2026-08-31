from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from users.models import FanProfile, GuestFavorite
from notifications.models import UserDevice
from notifications.services import NotificationService

def update_subscription_for_devices(devices, topic_base, action):
    for device in devices:
        if not device.registration_id:
            continue
        lang = device.language or 'en'
        topic_base_with_lang = f"{topic_base}_{lang}"
        
        if action == "post_add":
            try:
                NotificationService.subscribe_tokens_to_topic([device.registration_id], topic_base)
                NotificationService.subscribe_tokens_to_topic([device.registration_id], topic_base_with_lang)
            except Exception as e:
                print(f"Error subscribing device {device.id} to {topic_base}/{topic_base_with_lang}: {e}")
        elif action == "post_remove":
            try:
                NotificationService.unsubscribe_tokens_from_topic([device.registration_id], topic_base)
                NotificationService.unsubscribe_tokens_from_topic([device.registration_id], topic_base_with_lang)
            except Exception as e:
                print(f"Error unsubscribing device {device.id} from {topic_base}/{topic_base_with_lang}: {e}")

# ==========================================
# FanProfile Signals   
# ==========================================

@receiver(m2m_changed, sender=FanProfile.favorite_teams.through)
def update_fan_team_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    if not instance.receive_live_notifications:
        return
    devices = instance.user.devices.filter(active=True)
    for team_id in pk_set:
        update_subscription_for_devices(devices, f"team_{team_id}", action)

@receiver(m2m_changed, sender=FanProfile.favorite_leagues.through)
def update_fan_league_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    if not instance.receive_news_updates:
        return
    devices = instance.user.devices.filter(active=True)
    for league_id in pk_set:
        update_subscription_for_devices(devices, f"league_{league_id}", action)

@receiver(m2m_changed, sender=FanProfile.favorite_fixtures.through)
def update_fan_fixture_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    if not instance.receive_live_notifications:
        return
    devices = instance.user.devices.filter(active=True)
    for fixture_id in pk_set:
        for prefix in ["match", "fixture"]:
            update_subscription_for_devices(devices, f"{prefix}_{fixture_id}", action)

# ==========================================
# GuestFavorite Signals
# ==========================================

@receiver(m2m_changed, sender=GuestFavorite.favorite_teams.through)
def update_guest_team_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    devices = UserDevice.objects.filter(guest_id=instance.device_id, active=True)
    for team_id in pk_set:
        update_subscription_for_devices(devices, f"team_{team_id}", action)

@receiver(m2m_changed, sender=GuestFavorite.favorite_leagues.through)
def update_guest_league_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    devices = UserDevice.objects.filter(guest_id=instance.device_id, active=True)
    for league_id in pk_set:
        update_subscription_for_devices(devices, f"league_{league_id}", action)

@receiver(m2m_changed, sender=GuestFavorite.favorite_fixtures.through)
def update_guest_fixture_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    devices = UserDevice.objects.filter(guest_id=instance.device_id, active=True)
    for fixture_id in pk_set:
        for prefix in ["match", "fixture"]:
            update_subscription_for_devices(devices, f"{prefix}_{fixture_id}", action)