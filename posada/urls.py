from django.urls import path
from . import views

urlpatterns = [
    path('api/status/', views.guild_status, name='guild_status'),
    path('api/session/start/', views.start_session, name='start_session'),
    path('api/session/complete/', views.complete_session, name='complete_session'),
    path('api/adventurer/create/', views.create_adventurer,
         name='create_adventurer'),
    path('api/guild/consolidate/', views.consolidate_guild_wealth,
         name='consolidate_wealth'),
    path('api/guild/reset/', views.reset_guild, name='reset_guild'),
    path('api/adventurer/<int:adv_id>/consolidate/',
         views.consolidate_adventurer_wealth, name='consolidate_adventurer_wealth'),
    path('api/adventurer/delete/<int:adv_id>/',
         views.delete_adventurer, name='delete_adventurer'),
    path('api/adventurer/<int:adv_id>/rename/',
         views.rename_adventurer, name='rename_adventurer'),
    path('api/tavern/', views.tavern_recruits, name='tavern_recruits'),
    path('api/habits/', views.list_habits, name='list_habits'),
    path('api/habits/create/', views.create_habit, name='create_habit'),
    path('api/habits/complete/', views.complete_habit, name='complete_habit'),
    path('api/stats/graph/', views.get_stats_data, name='get_stats_data'),
    path('api/inventory/<str:target_type>/<int:target_id>/',
         views.get_inventory, name='get_inventory'),
    path('api/inventory/action/', views.inventory_action, name='inventory_action'),
    path('api/charts/', views.list_charts, name='list_charts'),
    path('api/charts/add_point/', views.add_chart_point, name='add_chart_point'),
    path('api/charts/create/', views.create_chart, name='create_chart'),
    path('api/charts/delete/<int:chart_id>/',
         views.delete_chart, name='delete_chart'),
    path('api/habits/delete/<int:habit_id>/',
         views.delete_habit, name='delete_habit'),
    path('api/habits/undo/',
         views.undo_habit, name='undo_habit'),
    path('api/charts/claim/', views.claim_chart_reward, name='claim_chart_reward'),
    path('api/adventurer/<int:adv_id>/unequip/',
         views.unequip_item, name='unequip_item'),
    path('api/journal/', views.list_journal, name='list_journal'),
    path('api/journal/create/', views.create_journal_entry,
         name='create_journal_entry'),
    path('api/guild/upgrades/', views.list_upgrades, name='list_upgrades'),
    path('api/guild/upgrades/buy/', views.buy_upgrade, name='buy_upgrade'),
    path('api/guild/exchange/', views.exchange_currency, name='exchange_currency'),

    # Kanban URLs
    path('api/kanban/', views.list_kanban, name='list_kanban'),
    path('api/kanban/column/create/', views.create_kanban_column, name='create_kanban_column'),
    path('api/kanban/task/create/', views.create_kanban_task, name='create_kanban_task'),
    path('api/kanban/task/move/', views.move_kanban_task, name='move_kanban_task'),
    path('api/kanban/task/edit/<int:task_id>/', views.edit_kanban_task, name='edit_kanban_task'),
    path('api/kanban/task/delete/<int:task_id>/', views.delete_kanban_task, name='delete_kanban_task'),
    path('api/kanban/column/delete/<int:col_id>/', views.delete_kanban_column, name='delete_kanban_column'),

    # Calendar URLs
    path('api/calendar/<int:year>/<int:month>/', views.list_calendar_events, name='list_calendar_events'),
    path('api/calendar/event/create/', views.create_calendar_event, name='create_calendar_event'),
    path('api/calendar/event/edit/<int:event_id>/', views.edit_calendar_event, name='edit_calendar_event'),
    path('api/calendar/event/delete/<int:event_id>/', views.delete_calendar_event, name='delete_calendar_event'),

    # Bestiary URLs
    path('api/bestiary/', views.list_bestiary, name='list_bestiary'),

    # Chronicles URLs
    path('api/chronicles/', views.list_chronicles, name='list_chronicles'),
]
