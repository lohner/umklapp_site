from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

class Teller(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    corresponding_story = models.ForeignKey('Story', on_delete=models.CASCADE,
                                            related_name="tellers")
    position = models.IntegerField()
    hasLeft = models.BooleanField()

class Story(models.Model):
    MINIMUM_NUMBER_OF_ACTIVE_TELLERS = 2
    started_by = models.ForeignKey(User, related_name="started_by", on_delete=models.CASCADE)
    title = models.CharField(max_length=256)
    whose_turn = models.IntegerField()
    is_finished = models.BooleanField()
    is_public = models.BooleanField(default=False,blank=False)

    def __unicode__(self):
        return self.title

    @staticmethod
    def create_new_story(startUser, participating_users, title, first_sentence):
        s = Story(started_by=startUser, is_finished=False, title=title, whose_turn=1)
        s.save()
        t0 = Teller(user=startUser, corresponding_story=s, position=0,
                    hasLeft=False)
        t0.save()
        firstPart = StoryPart(teller=t0, position=0, content=first_sentence)
        firstPart.save()

        positions = range(1, len(participating_users)+1)
        for (u,p) in zip(participating_users, positions):
            t = Teller(user=u, corresponding_story=s, position=p, hasLeft=False)
            t.save()
        return s

    def waiting_for_teller(self):
        if not self.is_finished:
            return Teller.objects.get(corresponding_story=self,position=self.whose_turn)
        else:
            return None

    def waiting_for(self):
        teller = self.waiting_for_teller()
        if teller:
            return teller.user
        else:
            return None

    def continue_story(self, text):
        last_part = self.latest_story_part()
        nextPos = last_part.position + 1
        newPart = StoryPart(teller=self.waiting_for_teller(), content=text, position=nextPos)
        newPart.save()
        self.advance_teller()

    def numberOfActiveTellers(self):
        return Teller.objects \
           .filter(corresponding_story=self, user__is_active = True, hasLeft = False) \
           .count()

    def leave_story(self, user):
        # capture the case that the teller leaves behind only one active person
        if (self.numberOfActiveTellers() <= Story.MINIMUM_NUMBER_OF_ACTIVE_TELLERS):
            raise NotEnoughActivePlayers

        # mark corresponding teller as 'has left'
        t0 = Teller.objects.get(corresponding_story=self, user=user)
        t0.hasLeft = True
        t0.save()

        # if it was the leaving teller's turn, fast forward to the next active
        # teller - note that there are at least two active tellers, so that
        # advance_teller will terminate
        if self.waiting_for() == user:
            self.advance_teller()

    def finish(self):
        self.is_finished = True
        self.save()

    def publish(self):
        self.is_public = True
        self.save()

    def parts(self):
        return StoryPart.objects.filter(teller__corresponding_story=self)

    def advance_teller(self):
        self.whose_turn = (self.whose_turn + 1) % self.tellers.count()
        while (not self.waiting_for().is_active or self.hasLeft(self.waiting_for())):
            self.whose_turn = (self.whose_turn + 1) % self.tellers.count()
        self.save()

    def hasLeft(self, user):
        t0 = Teller.objects.get(corresponding_story=self, user=user)
        return t0.hasLeft
    def latest_story_part(self):
        return self.parts().last()

    def participates_in(self, user):
        tellers = Teller.objects.filter(corresponding_story=self)
        for t in tellers:
            if t.user == user:
                return True
        return False

class StoryPart(models.Model):
    teller = models.ForeignKey('Teller', on_delete=models.CASCADE)
    position = models.IntegerField()
    content = models.CharField(max_length=256)

    class Meta:
        ordering = ['position']


class NotEnoughActivePlayers(Exception):
    pass
