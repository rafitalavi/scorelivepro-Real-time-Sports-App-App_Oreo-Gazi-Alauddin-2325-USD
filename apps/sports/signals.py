import sys
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.db import transaction
from users.models import FanProfile, GuestFavorite
from notifications.models import UserDevice
from notifications.services import NotificationService


def update_subscription_for_devices(devices, prefix_or_topic, item_id_or_action, is_subscribe=None):
    """
    Asynchronously update FCM topic subscriptions for given devices.
    Supports both:
      - New signature: update_subscription_for_devices(devices, prefix, item_id, is_subscribe=True)
      - Legacy signature: update_subscription_for_devices(devices, topic_base, action)
    """
    if is_subscribe is None:
        topic_base = prefix_or_topic
        action = item_id_or_action
        is_sub = (action == "post_add")
        if "_" in topic_base:
            parts = topic_base.split("_", 1)
            prefix = parts[0]
            item_id = parts[1]
        else:
            prefix = topic_base
            item_id = ""
    else:
        prefix = prefix_or_topic
        item_id = item_id_or_action
        is_sub = bool(is_subscribe)

    device_ids = list(devices.values_list('id', flat=True)) if hasattr(devices, 'values_list') else [d.id for d in devices]
    if not device_ids:
        return

    from notifications.tasks import sync_device_topic_async_task
    if 'test' in sys.argv:
        sync_device_topic_async_task(device_ids, prefix, item_id, is_subscribe=is_sub)
    else:
        transaction.on_commit(lambda: sync_device_topic_async_task.delay(device_ids, prefix, item_id, is_subscribe=is_sub))


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
    is_sub = (action == "post_add")
    for team_id in pk_set:
        update_subscription_for_devices(devices, "team", team_id, is_subscribe=is_sub)

@receiver(m2m_changed, sender=FanProfile.favorite_leagues.through)
def update_fan_league_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    if not instance.receive_news_updates:
        return
    devices = instance.user.devices.filter(active=True)
    is_sub = (action == "post_add")
    for league_id in pk_set:
        update_subscription_for_devices(devices, "league", league_id, is_subscribe=is_sub)

@receiver(m2m_changed, sender=FanProfile.favorite_fixtures.through)
def update_fan_fixture_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    if not instance.receive_live_notifications:
        return
    devices = instance.user.devices.filter(active=True)
    is_sub = (action == "post_add")
    for fixture_id in pk_set:
        update_subscription_for_devices(devices, "match", fixture_id, is_subscribe=is_sub)

# ==========================================
# GuestFavorite Signals
# ==========================================

@receiver(m2m_changed, sender=GuestFavorite.favorite_teams.through)
def update_guest_team_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    devices = UserDevice.objects.filter(guest_id=instance.device_id, active=True)
    is_sub = (action == "post_add")
    for team_id in pk_set:
        update_subscription_for_devices(devices, "team", team_id, is_subscribe=is_sub)

@receiver(m2m_changed, sender=GuestFavorite.favorite_leagues.through)
def update_guest_league_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    devices = UserDevice.objects.filter(guest_id=instance.device_id, active=True)
    is_sub = (action == "post_add")
    for league_id in pk_set:
        update_subscription_for_devices(devices, "league", league_id, is_subscribe=is_sub)

@receiver(m2m_changed, sender=GuestFavorite.favorite_fixtures.through)
def update_guest_fixture_subscription(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ["post_add", "post_remove"]:
        return
    devices = UserDevice.objects.filter(guest_id=instance.device_id, active=True)
    is_sub = (action == "post_add")
    for fixture_id in pk_set:
        update_subscription_for_devices(devices, "match", fixture_id, is_subscribe=is_sub)