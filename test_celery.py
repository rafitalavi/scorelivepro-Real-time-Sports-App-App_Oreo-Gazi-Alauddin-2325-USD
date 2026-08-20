#!/usr/bin/env python
"""
Quick script to test if Celery is working properly.
Run this from the project root: python test_celery.py
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')
django.setup()

from sports.tasks import fetch_timezones, fetch_countries, update_live_fixtures

def test_celery():
    print("🧪 Testing Celery...")
    print("\n1. Testing simple task (fetch_timezones)...")
    result = fetch_timezones.delay()
    print(f"   Task ID: {result.id}")
    print(f"   Task State: {result.state}")
    print(f"   Waiting for result...")
    try:
        task_result = result.get(timeout=30)
        print(f"   ✅ Task completed: {task_result}")
    except Exception as e:
        print(f"   ❌ Task failed: {e}")
    
    print("\n2. Testing another task (fetch_countries)...")
    result2 = fetch_countries.delay()
    print(f"   Task ID: {result2.id}")
    print(f"   Task State: {result2.state}")
    try:
        task_result2 = result2.get(timeout=30)
        print(f"   ✅ Task completed: {task_result2}")
    except Exception as e:
        print(f"   ❌ Task failed: {e}")
    
    print("\n✅ Celery test complete!")
    print("\nTo check task status manually:")
    print(f"   from celery.result import AsyncResult")
    print(f"   result = AsyncResult('{result.id}')")
    print(f"   print(result.state)")

if __name__ == '__main__':
    test_celery()

