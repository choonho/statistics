import logging

from spaceone.core.service import *
from spaceone.statistics.error import *
from spaceone.statistics.manager.resource_manager import ResourceManager
from spaceone.statistics.manager.schedule_manager import ScheduleManager
from spaceone.statistics.manager.history_manager import HistoryManager

_LOGGER = logging.getLogger(__name__)


@authentication_handler
@authorization_handler
@event_handler
class HistoryService(BaseService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resource_mgr: ResourceManager = self.locator.get_manager('ResourceManager')
        self.history_mgr: HistoryManager = self.locator.get_manager('HistoryManager')

    @transaction
    @check_required(['schedule_id', 'domain_id'])
    def create(self, params):
        """Statistics query to resource

        Args:
            params (dict): {
                'schedule_id': 'str',
                'domain_id': 'str'
            }

        Returns:
            None
        """

        schedule_mgr: ScheduleManager = self.locator.get_manager('ScheduleManager')

        domain_id = params['domain_id']
        schedule_id = params['schedule_id']

        schedule_vo = schedule_mgr.get_schedule(schedule_id, domain_id, ['topic', 'options'])
        schedule_data = schedule_vo.to_dict()
        topic = schedule_data['topic']
        options = schedule_data['options']
        resource_type = options['resource_type']
        query = options.get('query', {})
        distinct = query.get('distinct')
        join = list(map(lambda j: j.to_dict(), options.get('join', [])))
        formulas = list(map(lambda f: f.to_dict(), options.get('formulas', [])))
        sort = query.get('sort')
        page = query.get('page', {})
        limit = query.get('limit')
        has_join_or_formula = len(join) > 0 or len(formulas) > 0

        if distinct:
            if has_join_or_formula:
                raise ERROR_STATISTICS_DISTINCT()
        else:
            if has_join_or_formula:
                query['sort'] = None
                query['page'] = None
                query['limit'] = None

        response = self.resource_mgr.stat(resource_type, query, domain_id)
        if len(join) > 0 or len(formulas) > 0:
            results = response.get('results', [])
            response = self.resource_mgr.join_and_execute_formula(results, resource_type,
                                                                  query, join, formulas, sort,
                                                                  page, limit, domain_id)

        results = response.get('results', [])
        self.history_mgr.create_history(schedule_vo, topic, results, domain_id)

    @transaction
    @check_required(['topic', 'domain_id'])
    @append_query_filter(['topic', 'domain_id'])
    @append_keyword_filter(['topic'])
    def list(self, params):
        """ List history

        Args:
            params (dict): {
                'topic': 'str',
                'domain_id': 'str',
                'query': 'dict (spaceone.api.core.v1.Query)'
            }

        Returns:
            history_vos (object)
            total_count
        """

        query = params.get('query', {})
        return self.history_mgr.list_history(query)

    @transaction
    @check_required(['topic', 'query', 'domain_id'])
    @append_query_filter(['topic', 'domain_id'])
    def stat(self, params):
        """
        Args:
            params (dict): {
                'domain_id': 'str',
                'query': 'dict (spaceone.api.core.v1.StatisticsQuery)'
            }

        Returns:
            values (list) : 'list of statistics data'

        """

        query = params.get('query', {})
        return self.history_mgr.stat_history(query)
