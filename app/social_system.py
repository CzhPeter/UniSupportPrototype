from datetime import datetime


class User:
    def __init__(self, name:str, email:str, role:str):
        self.name = name
        self.email = email
        self.role = role


class Poster(User):
    def __init__(self, name:str, email:str):
        super().__init__(name, email, "poster")

    def __repr__(self):
        return f"Poster(name={self.name}, email={self.email}, role={self.role})"

class Notification:
    def __init__(self,  content:str, poster:Poster, date:datetime):
        self.content = content
        self.poster = poster
        self.date = date

    def __repr__(self):
        return f"Notification(content={self.content}, poster={self.poster.name}, date={self.date})"

class Subscriber(User):
    def __init__(self, name:str, email:str):
        super().__init__(name, email, "subscriber")
        self.notifications = []

    def __repr__(self):
        return f"Subscriber(name={self.name}, email={self.email}, role={self.role}, notifications={self.notifications})"


class Topic:
    def __init__(self, description:str, name:str = ''):
        self.name = name
        self.description = description
        self.notifications = []
        self.subscribers = []
        self.posters = []

    def add_subscriber(self, subscriber:Subscriber):
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)

    def delete_subscriber(self, subscriber:Subscriber):
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)

    def add_poster(self, poster:Poster):
        if poster not in self.posters:
            self.posters.append(poster)

    def post_notification(self, poster:Poster, notification:Notification):
        if poster in self.posters:
            self.notifications.append(notification)
            for subscriber in self.subscribers:
                subscriber.notifications.append(notification)


poster1 = Poster("Post 1", "<EMAIL>")
subscriber1 = Subscriber("Subscriber1", "<EMAIL>")
topic1 = Topic("Topic 1", "testTopic")

topic1.add_subscriber(subscriber1)
topic1.add_poster(poster1)

notification1 = Notification("Test Notification", poster1, datetime.now())
topic1.post_notification(poster1, notification1)

print(topic1.notifications)
print(topic1.posters)
print(topic1.subscribers)



