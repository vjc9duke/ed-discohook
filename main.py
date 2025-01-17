import os
import asyncio
import requests
import logging as log

from dotenv import load_dotenv
from datetime import datetime, timezone
from edspy import edspy

from static import *

# webhook url that can be loaded from .env with same name (see .env.example)
COURSE_IDS = {
    72681: 'ECE_350_WEBHOOK',
    72536: 'COMPSCI_308_WEBHOOK',
    73072: 'TEST_WEBHOOK'
}

class EventHandler:

    def __init__(self, client: edspy.EdClient, webhooks: dict) -> None:
        self.client = client
        self.webhooks = webhooks
        self.courses = None
    
    async def update_courses(self):
        # update user courses cache every hour
        while True:
            self.courses = await self.client.get_courses()
            await asyncio.sleep(3600)
 
    @edspy.listener(edspy.ThreadNewEvent)
    async def on_new_thread(self, event: edspy.ThreadNewEvent):

        thread: edspy.Thread = event.thread

        if not self.courses:
            await self.update_courses()
        course = next(filter(lambda x: x.id == thread.course_id, self.courses), None)

        # send payload to Discord
        requests.post(
            url=self.webhooks.get(course.id),
            json={
                'username': 'Ed',
                'avatar_url': ED_ICON,
                'embeds': self.build_embed(thread, course)
            })

    @staticmethod
    def build_embed(thread: edspy.Thread, course: edspy.Course):

        return [{
            'title': '#{} **{}**'.format(thread.number, thread.title),
            'description': thread.document,
            'url': BASE_URL + '/courses/{}/discussion/{}'.format(thread.course_id, thread.id),
            'color': EMBED_COLORS.get(thread.type, UKNOWN_COLOR),
            'author': {
                'name': '{} • {}'.format(course.code, thread.category),
                'url': BASE_URL + '/courses/{}/discussion'.format(thread.course_id)},
            'footer': {
                'text': 'Anonymous User' if thread.is_anonymous else 'Name Hidden',
                'icon_url': USER_ICON
            },
            'timestamp': f'{datetime.now(timezone.utc).isoformat()[:-9]}Z'
        }]

async def main():
    load_dotenv()

    webhook_urls = {course_id: os.getenv(webhook) for 
        course_id, webhook in COURSE_IDS.items()}

    client = edspy.EdClient()
    handler = EventHandler(client=client, webhooks=webhook_urls)
    client.add_event_hooks(handler)
    
    await asyncio.gather(
        handler.update_courses(),
        client.subscribe(list(webhook_urls.keys())))

if __name__ == '__main__':
    log.basicConfig(level=log.INFO)
    asyncio.run(main())