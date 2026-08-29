from celery import shared_task
from .models import UserDevice
from .services import sync_device_subscriptions, update_device_topic_subscriptions

@shared_task
def sync_device_subscriptions_task(device_id):
    try:
        device = UserDevice.objects.get(id=device_id)
        sync_device_subscriptions(device)
    except UserDevice.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error in sync_device_subscriptions_task: {e}")

@shared_task
def update_device_topic_subscriptions_task(device_id, old_lang, new_lang):
    try:
        device = UserDevice.objects.get(id=device_id)
        update_device_topic_subscriptions(device, old_lang, new_lang)
    except UserDevice.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error in update_device_topic_subscriptions_task: {e}")
