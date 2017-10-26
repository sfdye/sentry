from __future__ import absolute_import

import six
from collections import defaultdict

from sentry.api.serializers import Serializer, register, serialize
from sentry.models import OrganizationMember, OrganizationMemberTeam, Team


@register(OrganizationMember)
class OrganizationMemberSerializer(Serializer):
    def get_attrs(self, item_list, user):
        # TODO(dcramer): assert on relations
        users = {d['id']: d for d in serialize(
            set(i.user for i in item_list if i.user_id), user)}

        return {
            item: {
                'user': users[six.text_type(item.user_id)] if item.user_id else None,
            } for item in item_list
        }

    def serialize(self, obj, attrs, user):
        d = {
            'id': six.text_type(obj.id),
            'email': obj.get_email(),
            'name': obj.user.get_display_name() if obj.user else obj.get_email(),
            'user': attrs['user'],
            'role': obj.role,
            'roleName': obj.get_role_display(),
            'pending': obj.is_pending,
            'flags': {
                'sso:linked': bool(getattr(obj.flags, 'sso:linked')),
                'sso:invalid': bool(getattr(obj.flags, 'sso:invalid')),
            },
            'dateCreated': obj.date_added,
        }
        return d


class OrganizationMemberWithTeamsSerializer(OrganizationMemberSerializer):
    def get_attrs(self, item_list, user):
        attrs = super(OrganizationMemberWithTeamsSerializer,
                      self).get_attrs(item_list, user)

        member_team_map = OrganizationMemberTeam.objects.values(
            'organizationmember', 'team')

        teams = {t.id: t for t in Team.objects.filter(
            id__in=[item['team'] for item in member_team_map])}
        results = defaultdict(list)

        # results is a map of member id -> team_slug[]
        for m in member_team_map:
            results[m['organizationmember']].append(teams[m['team']].slug)

        for item in item_list:
            teams = results[item.id] if item.id in results else []
            try:
                attrs[item]['teams'] = teams
            except KeyError:
                attrs[item] = {
                    'teams': teams
                }

        return attrs

    def serialize(self, obj, attrs, user):
        d = super(OrganizationMemberWithTeamsSerializer,
                  self).serialize(obj, attrs, user)

        try:
            d['teams'] = attrs['teams']
        except KeyError:
            pass

        return d
