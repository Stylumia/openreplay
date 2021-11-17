from decouple import config
from fastapi import Depends, Body

import schemas
from chalicelib.core import log_tool_rollbar, sourcemaps, events, sessions_assignments, projects, \
    sessions_metas, alerts, funnels, issues, integrations_manager, metadata, \
    log_tool_elasticsearch, log_tool_datadog, \
    log_tool_stackdriver, reset_password, sessions_favorite_viewed, \
    log_tool_cloudwatch, log_tool_sentry, log_tool_sumologic, log_tools, errors, sessions, \
    log_tool_newrelic, announcements, log_tool_bugsnag, weekly_report, integration_jira_cloud, integration_github, \
    assist, heatmaps, mobile
from chalicelib.core.collaboration_slack import Slack
from chalicelib.utils import email_helper
from or_dependencies import OR_context
from routers.base import get_routers

public_app, app, app_apikey = get_routers()


@app.get('/{projectId}/sessions2/favorite', tags=["sessions"])
def get_favorite_sessions(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {
        'data': sessions.get_favorite_sessions(project_id=projectId, user_id=context.user_id, include_viewed=True)
    }


@app.get('/{projectId}/sessions2/{sessionId}', tags=["sessions"])
def get_session2(projectId: int, sessionId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = sessions.get_by_id2_pg(project_id=projectId, session_id=sessionId, full_data=True, user_id=context.user_id,
                                  include_fav_viewed=True, group_metadata=True)
    if data is None:
        return {"errors": ["session not found"]}

    sessions_favorite_viewed.view_session(project_id=projectId, user_id=context.user_id, session_id=sessionId)
    return {
        'data': data
    }


@app.get('/{projectId}/sessions2/{sessionId}/favorite', tags=["sessions"])
def add_remove_favorite_session2(projectId: int, sessionId: int,
                                 context: schemas.CurrentContext = Depends(OR_context)):
    return {
        "data": sessions_favorite_viewed.favorite_session(project_id=projectId, user_id=context.user_id,
                                                          session_id=sessionId)}


@app.get('/{projectId}/sessions2/{sessionId}/assign', tags=["sessions"])
def assign_session(projectId: int, sessionId, context: schemas.CurrentContext = Depends(OR_context)):
    data = sessions_assignments.get_by_session(project_id=projectId, session_id=sessionId,
                                               tenant_id=context.tenant_id,
                                               user_id=context.user_id)
    if "errors" in data:
        return data
    return {
        'data': data
    }


@app.get('/{projectId}/sessions2/{sessionId}/errors/{errorId}/sourcemaps', tags=["sessions", "sourcemaps"])
def get_error_trace(projectId: int, sessionId: int, errorId: str,
                    context: schemas.CurrentContext = Depends(OR_context)):
    data = errors.get_trace(project_id=projectId, error_id=errorId)
    if "errors" in data:
        return data
    return {
        'data': data
    }


@app.get('/{projectId}/sessions2/{sessionId}/assign/{issueId}', tags=["sessions", "issueTracking"])
def assign_session(projectId: int, sessionId: int, issueId: int,
                   context: schemas.CurrentContext = Depends(OR_context)):
    data = sessions_assignments.get(project_id=projectId, session_id=sessionId, assignment_id=issueId,
                                    tenant_id=context.tenant_id, user_id=context.user_id)
    if "errors" in data:
        return data
    return {
        'data': data
    }


@app.post('/{projectId}/sessions2/{sessionId}/assign/{issueId}/comment', tags=["sessions", "issueTracking"])
@app.put('/{projectId}/sessions2/{sessionId}/assign/{issueId}/comment', tags=["sessions", "issueTracking"])
def comment_assignment(projectId: int, sessionId: int, issueId: int, data: schemas.CommentAssignmentSchema = Body(...),
                       context: schemas.CurrentContext = Depends(OR_context)):
    data = sessions_assignments.comment(tenant_id=context.tenant_id, project_id=projectId,
                                        session_id=sessionId, assignment_id=issueId,
                                        user_id=context.user_id, message=data.message)
    if "errors" in data.keys():
        return data
    return {
        'data': data
    }


@app.get('/{projectId}/events/search', tags=["events"])
def events_search(projectId: int, q: str, type: str = None, key: str = None, source: str = None,
                  context: schemas.CurrentContext = Depends(OR_context)):
    if len(q) == 0:
        return {"data": []}
    result = events.search_pg2(text=q, event_type=type, project_id=projectId, source=source,
                               key=key)
    return result


@app.post('/{projectId}/sessions/search2', tags=["sessions"])
def sessions_search2(projectId: int, data: schemas.SessionsSearchPayloadSchema = Body(...),
                     context: schemas.CurrentContext = Depends(OR_context)):
    data = sessions.search2_pg(data.dict(), projectId, user_id=context.user_id)
    return {'data': data}


@app.get('/{projectId}/sessions/filters', tags=["sessions"])
def session_filter_values(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {'data': sessions_metas.get_key_values(projectId)}


@app.get('/{projectId}/sessions/filters/top', tags=["sessions"])
def session_top_filter_values(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {'data': sessions_metas.get_top_key_values(projectId)}


@app.get('/{projectId}/sessions/filters/search', tags=["sessions"])
def get_session_filters_meta(projectId: int, q: str, type: str,
                             context: schemas.CurrentContext = Depends(OR_context)):
    meta_type = type
    if len(meta_type) == 0:
        return {"data": []}
    if len(q) == 0:
        return {"data": []}
    return sessions_metas.search(project_id=projectId, meta_type=meta_type, text=q)


@app.post('/{projectId}/integrations/{integration}/notify/{integrationId}/{source}/{sourceId}', tags=["integrations"])
@app.put('/{projectId}/integrations/{integration}/notify/{integrationId}/{source}/{sourceId}', tags=["integrations"])
def integration_notify(projectId: int, integration: str, integrationId: int, source: str, sourceId: str,
                       data: schemas.IntegrationNotificationSchema = Body(...),
                       context: schemas.CurrentContext = Depends(OR_context)):
    comment = None
    if data.comment:
        comment = data.comment
    if integration == "slack":
        args = {"tenant_id": context.tenant_id,
                "user": context.email, "comment": comment, "project_id": projectId,
                "integration_id": integrationId}
        if source == "sessions":
            return Slack.share_session(session_id=sourceId, **args)
        elif source == "errors":
            return Slack.share_error(error_id=sourceId, **args)
    return {"data": None}


@app.get('/integrations/sentry', tags=["integrations"])
def get_all_sentry(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/sentry', tags=["integrations"])
def get_sentry(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.get(project_id=projectId)}


@app.post('/{projectId}/integrations/sentry', tags=["integrations"])
@app.put('/{projectId}/integrations/sentry', tags=["integrations"])
def add_edit_sentry(projectId: int, data: schemas.SentrySchema = Body(...),
                    context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/sentry', tags=["integrations"])
def delete_sentry(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.get('/{projectId}/integrations/sentry/events/{eventId}', tags=["integrations"])
def proxy_sentry(projectId: int, eventId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sentry.proxy_get(tenant_id=context.tenant_id, project_id=projectId, event_id=eventId)}


@app.get('/integrations/datadog', tags=["integrations"])
def get_all_datadog(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_datadog.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/datadog', tags=["integrations"])
def get_datadog(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_datadog.get(project_id=projectId)}


@app.post('/{projectId}/integrations/datadog', tags=["integrations"])
@app.put('/{projectId}/integrations/datadog', tags=["integrations"])
def add_edit_datadog(projectId: int, data: schemas.DatadogSchema = Body(...),
                     context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_datadog.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/datadog', tags=["integrations"])
def delete_datadog(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_datadog.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.get('/integrations/stackdriver', tags=["integrations"])
def get_all_stackdriver(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_stackdriver.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/stackdriver', tags=["integrations"])
def get_stackdriver(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_stackdriver.get(project_id=projectId)}


@app.post('/{projectId}/integrations/stackdriver', tags=["integrations"])
@app.put('/{projectId}/integrations/stackdriver', tags=["integrations"])
def add_edit_stackdriver(projectId: int, data: schemas.StackdriverSchema = Body(...),
                         context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_stackdriver.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/stackdriver', tags=["integrations"])
def delete_stackdriver(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_stackdriver.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.get('/integrations/newrelic', tags=["integrations"])
def get_all_newrelic(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_newrelic.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/newrelic', tags=["integrations"])
def get_newrelic(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_newrelic.get(project_id=projectId)}


@app.post('/{projectId}/integrations/newrelic', tags=["integrations"])
@app.put('/{projectId}/integrations/newrelic', tags=["integrations"])
def add_edit_newrelic(projectId: int, data: schemas.NewrelicSchema = Body(...),
                      context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_newrelic.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/newrelic', tags=["integrations"])
def delete_newrelic(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_newrelic.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.get('/integrations/rollbar', tags=["integrations"])
def get_all_rollbar(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_rollbar.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/rollbar', tags=["integrations"])
def get_rollbar(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_rollbar.get(project_id=projectId)}


@app.post('/{projectId}/integrations/rollbar', tags=["integrations"])
@app.put('/{projectId}/integrations/rollbar', tags=["integrations"])
def add_edit_rollbar(projectId: int, data: schemas.RollbarSchema = Body(...),
                     context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_rollbar.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/rollbar', tags=["integrations"])
def delete_datadog(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_rollbar.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.post('/integrations/bugsnag/list_projects', tags=["integrations"])
def list_projects_bugsnag(data: schemas.BugsnagBasicSchema = Body(...),
                          context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_bugsnag.list_projects(auth_token=data.authorizationToken)}


@app.get('/integrations/bugsnag', tags=["integrations"])
def get_all_bugsnag(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_bugsnag.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/bugsnag', tags=["integrations"])
def get_bugsnag(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_bugsnag.get(project_id=projectId)}


@app.post('/{projectId}/integrations/bugsnag', tags=["integrations"])
@app.put('/{projectId}/integrations/bugsnag', tags=["integrations"])
def add_edit_bugsnag(projectId: int, data: schemas.BugsnagSchema = Body(...),
                     context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_bugsnag.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/bugsnag', tags=["integrations"])
def delete_bugsnag(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_bugsnag.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.post('/integrations/cloudwatch/list_groups', tags=["integrations"])
def list_groups_cloudwatch(data: schemas.CloudwatchBasicSchema = Body(...),
                           context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_cloudwatch.list_log_groups(aws_access_key_id=data.awsAccessKeyId,
                                                        aws_secret_access_key=data.awsSecretAccessKey,
                                                        region=data.region)}


@app.get('/integrations/cloudwatch', tags=["integrations"])
def get_all_cloudwatch(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_cloudwatch.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/cloudwatch', tags=["integrations"])
def get_cloudwatch(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_cloudwatch.get(project_id=projectId)}


@app.post('/{projectId}/integrations/cloudwatch', tags=["integrations"])
@app.put('/{projectId}/integrations/cloudwatch', tags=["integrations"])
def add_edit_cloudwatch(projectId: int, data: schemas.CloudwatchSchema = Body(...),
                        context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_cloudwatch.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/cloudwatch', tags=["integrations"])
def delete_cloudwatch(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_cloudwatch.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.get('/integrations/elasticsearch', tags=["integrations"])
def get_all_elasticsearch(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_elasticsearch.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/elasticsearch', tags=["integrations"])
def get_elasticsearch(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_elasticsearch.get(project_id=projectId)}


@app.post('/integrations/elasticsearch/test', tags=["integrations"])
def test_elasticsearch_connection(data: schemas.ElasticsearchBasicSchema = Body(...),
                                  context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_elasticsearch.ping(tenant_id=context.tenant_id, **data.dict())}


@app.post('/{projectId}/integrations/elasticsearch', tags=["integrations"])
@app.put('/{projectId}/integrations/elasticsearch', tags=["integrations"])
def add_edit_elasticsearch(projectId: int, data: schemas.ElasticsearchSchema = Body(...),
                           context: schemas.CurrentContext = Depends(OR_context)):
    return {
        "data": log_tool_elasticsearch.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/elasticsearch', tags=["integrations"])
def delete_elasticsearch(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_elasticsearch.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.get('/integrations/sumologic', tags=["integrations"])
def get_all_sumologic(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sumologic.get_all(tenant_id=context.tenant_id)}


@app.get('/{projectId}/integrations/sumologic', tags=["integrations"])
def get_sumologic(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sumologic.get(project_id=projectId)}


@app.post('/{projectId}/integrations/sumologic', tags=["integrations"])
@app.put('/{projectId}/integrations/sumologic', tags=["integrations"])
def add_edit_sumologic(projectId: int, data: schemas.SumologicSchema = Body(...),
                       context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sumologic.add_edit(tenant_id=context.tenant_id, project_id=projectId, data=data.dict())}


@app.delete('/{projectId}/integrations/sumologic', tags=["integrations"])
def delete_sumologic(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": log_tool_sumologic.delete(tenant_id=context.tenant_id, project_id=projectId)}


@app.get('/integrations/issues', tags=["integrations"])
def get_integration_status(context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tenant_id=context.tenant_id,
                                                              user_id=context.user_id)
    if error is not None:
        return {"data": {}}
    return {"data": integration.get_obfuscated()}


@app.post('/integrations/jira', tags=["integrations"])
@app.put('/integrations/jira', tags=["integrations"])
def add_edit_jira_cloud(data: schemas.JiraGithubSchema = Body(...),
                        context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tool=integration_jira_cloud.PROVIDER,
                                                              tenant_id=context.tenant_id,
                                                              user_id=context.user_id)
    if error is not None:
        return error
    data.provider = integration_jira_cloud.PROVIDER
    return {"data": integration.add_edit(data=data.dict())}


@app.post('/integrations/github', tags=["integrations"])
@app.put('/integrations/github', tags=["integrations"])
def add_edit_github(data: schemas.JiraGithubSchema = Body(...),
                    context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tool=integration_github.PROVIDER,
                                                              tenant_id=context.tenant_id,
                                                              user_id=context.user_id)
    if error is not None:
        return error
    data.provider = integration_github.PROVIDER
    return {"data": integration.add_edit(data=data.dict())}


@app.delete('/integrations/issues', tags=["integrations"])
def delete_default_issue_tracking_tool(context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tenant_id=context.tenant_id,
                                                              user_id=context.user_id)
    if error is not None:
        return error
    return {"data": integration.delete()}


@app.delete('/integrations/jira', tags=["integrations"])
def delete_jira_cloud(context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tool=integration_jira_cloud.PROVIDER,
                                                              tenant_id=context.tenant_id,
                                                              user_id=context.user_id)
    if error is not None:
        return error
    return {"data": integration.delete()}


@app.delete('/integrations/github', tags=["integrations"])
def delete_github(context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tool=integration_github.PROVIDER,
                                                              tenant_id=context.tenant_id,
                                                              user_id=context.user_id)
    if error is not None:
        return error
    return {"data": integration.delete()}


@app.get('/integrations/issues/list_projects', tags=["integrations"])
def get_all_issue_tracking_projects(context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tenant_id=context.tenant_id,
                                                              user_id=context.user_id)
    if error is not None:
        return error
    data = integration.issue_handler.get_projects()
    if "errors" in data:
        return data
    return {"data": data}


@app.get('/integrations/issues/{integrationProjectId}', tags=["integrations"])
def get_integration_metadata(integrationProjectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    error, integration = integrations_manager.get_integration(tenant_id=context.tenant_id,
                                                              user_id=context.user_id)
    if error is not None:
        return error
    data = integration.issue_handler.get_metas(integrationProjectId)
    if "errors" in data.keys():
        return data
    return {"data": data}


@app.get('/{projectId}/assignments', tags=["assignment"])
def get_all_assignments(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = sessions_assignments.get_all(project_id=projectId, user_id=context.user_id)
    return {
        'data': data
    }


@app.post('/{projectId}/sessions2/{sessionId}/assign/projects/{integrationProjectId}', tags=["assignment"])
@app.put('/{projectId}/sessions2/{sessionId}/assign/projects/{integrationProjectId}', tags=["assignment"])
def create_issue_assignment(projectId: int, sessionId: int, integrationProjectId,
                            data: schemas.AssignmentSchema = Body(...),
                            context: schemas.CurrentContext = Depends(OR_context)):
    data = sessions_assignments.create_new_assignment(tenant_id=context.tenant_id, project_id=projectId,
                                                      session_id=sessionId,
                                                      creator_id=context.user_id, assignee=data.assignee,
                                                      description=data.description, title=data.title,
                                                      issue_type=data.issue_type,
                                                      integration_project_id=integrationProjectId)
    if "errors" in data.keys():
        return data
    return {
        'data': data
    }


@app.get('/{projectId}/gdpr', tags=["projects", "gdpr"])
def get_gdpr(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": projects.get_gdpr(project_id=projectId)}


@app.post('/{projectId}/gdpr', tags=["projects", "gdpr"])
@app.put('/{projectId}/gdpr', tags=["projects", "gdpr"])
def edit_gdpr(projectId: int, data: schemas.GdprSchema = Body(...),
              context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": projects.edit_gdpr(project_id=projectId, gdpr=data.dict())}


@public_app.post('/password/reset-link', tags=["reset password"])
@public_app.put('/password/reset-link', tags=["reset password"])
def reset_password_handler(data: schemas.ForgetPasswordPayloadSchema = Body(...)):
    if len(data.email) < 5:
        return {"errors": ["please provide a valid email address"]}
    return reset_password.reset(data.dict())


@app.get('/{projectId}/metadata', tags=["metadata"])
def get_metadata(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": metadata.get(project_id=projectId)}


@app.post('/{projectId}/metadata/list', tags=["metadata"])
@app.put('/{projectId}/metadata/list', tags=["metadata"])
def add_edit_delete_metadata(projectId: int, data: schemas.MetadataListSchema = Body(...),
                             context: schemas.CurrentContext = Depends(OR_context)):
    return metadata.add_edit_delete(tenant_id=context.tenant_id, project_id=projectId, new_metas=data.list)


@app.post('/{projectId}/metadata', tags=["metadata"])
@app.put('/{projectId}/metadata', tags=["metadata"])
def add_metadata(projectId: int, data: schemas.MetadataBasicSchema = Body(...),
                 context: schemas.CurrentContext = Depends(OR_context)):
    return metadata.add(tenant_id=context.tenant_id, project_id=projectId, new_name=data.key)


@app.post('/{projectId}/metadata/{index}', tags=["metadata"])
@app.put('/{projectId}/metadata/{index}', tags=["metadata"])
def edit_metadata(projectId: int, index: int, data: schemas.MetadataBasicSchema = Body(...),
                  context: schemas.CurrentContext = Depends(OR_context)):
    return metadata.edit(tenant_id=context.tenant_id, project_id=projectId, index=int(index),
                         new_name=data.key)


@app.delete('/{projectId}/metadata/{index}', tags=["metadata"])
def delete_metadata(projectId: int, index: int, context: schemas.CurrentContext = Depends(OR_context)):
    return metadata.delete(tenant_id=context.tenant_id, project_id=projectId, index=index)


@app.get('/{projectId}/metadata/search', tags=["metadata"])
def search_metadata(projectId: int, q: str, key: str, context: schemas.CurrentContext = Depends(OR_context)):
    if len(q) == 0 and len(key) == 0:
        return {"data": []}
    if len(q) == 0:
        return {"errors": ["please provide a value for search"]}
    if len(key) == 0:
        return {"errors": ["please provide a key for search"]}
    return metadata.search(tenant_id=context.tenant_id, project_id=projectId, value=q, key=key)


@app.get('/{projectId}/integration/sources', tags=["integrations"])
def search_integrations(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return log_tools.search(project_id=projectId)


@public_app.post('/async/email_assignment', tags=["async mail"])
def async_send_signup_emails(data: schemas.EmailPayloadSchema = Body(...)):
    if data.auth != config("async_Token"):
        return {}
    email_helper.send_assign_session(recipient=data.email, link=data.link, message=data.message)


# TODO: transform this to a background task when you find a way to run it without an attached request
@public_app.post('/async/funnel/weekly_report2', tags=["async mail"])
def async_weekly_report(data: schemas.WeeklyReportPayloadSchema = Body(...)):
    print("=========================> Sending weekly report")
    if data.auth != config("async_Token"):
        return {}
    email_helper.weekly_report2(recipients=data.email, data=data.data)


# @public_app.post('/async/basic/member_invitation', tags=["async mail"])
# def async_basic_emails(data: schemas.MemberInvitationPayloadSchema = Body(...)):
#     if data.auth != config("async_Token"):
#         return {}
#     email_helper.send_team_invitation(recipient=data.email, invitation_link=data.invitation_link,
#                                       client_id=data.client_id, sender_name=data.sender_name)


@app.get('/{projectId}/sample_rate', tags=["projects"])
def get_capture_status(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": projects.get_capture_status(project_id=projectId)}


@app.post('/{projectId}/sample_rate', tags=["projects"])
@app.put('/{projectId}/sample_rate', tags=["projects"])
def update_capture_status(projectId: int, data: schemas.SampleRateSchema = Body(...),
                          context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": projects.update_capture_status(project_id=projectId, changes=data.dict())}


@app.get('/announcements', tags=["announcements"])
def get_all_announcements(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": announcements.get_all(context.user_id)}


@app.get('/announcements/view', tags=["announcements"])
def get_all_announcements(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": announcements.view(user_id=context.user_id)}


@app.post('/{projectId}/errors/merge', tags=["errors"])
def errors_merge(projectId: int, data: schemas.ErrorIdsPayloadSchema = Body(...),
                 context: schemas.CurrentContext = Depends(OR_context)):
    data = errors.merge(error_ids=data.errors)
    return data


@app.get('/show_banner', tags=["banner"])
def errors_merge(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": False}


@app.post('/{projectId}/alerts', tags=["alerts"])
@app.put('/{projectId}/alerts', tags=["alerts"])
def create_alert(projectId: int, data: schemas.AlertSchema = Body(...),
                 context: schemas.CurrentContext = Depends(OR_context)):
    return alerts.create(projectId, data.dict())


@app.get('/{projectId}/alerts', tags=["alerts"])
def get_all_alerts(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": alerts.get_all(projectId)}


@app.get('/{projectId}/alerts/{alertId}', tags=["alerts"])
def get_alert(projectId: int, alertId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": alerts.get(alertId)}


@app.post('/{projectId}/alerts/{alertId}', tags=["alerts"])
@app.put('/{projectId}/alerts/{alertId}', tags=["alerts"])
def update_alert(projectId: int, alertId: int, data: schemas.AlertSchema = Body(...),
                 context: schemas.CurrentContext = Depends(OR_context)):
    return alerts.update(alertId, data.dict())


@app.delete('/{projectId}/alerts/{alertId}', tags=["alerts"])
def delete_alert(projectId: int, alertId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return alerts.delete(projectId, alertId)


@app.post('/{projectId}/funnels', tags=["funnels"])
@app.put('/{projectId}/funnels', tags=["funnels"])
def add_funnel(projectId: int, data: schemas.FunnelSchema = Body(...),
               context: schemas.CurrentContext = Depends(OR_context)):
    return funnels.create(project_id=projectId,
                          user_id=context.user_id,
                          name=data.name,
                          filter=data.filter.dict(),
                          is_public=data.is_public)


@app.get('/{projectId}/funnels', tags=["funnels"])
def get_funnels(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": funnels.get_by_user(project_id=projectId,
                                        user_id=context.user_id,
                                        range_value=None,
                                        start_date=None,
                                        end_date=None,
                                        details=False)}


@app.get('/{projectId}/funnels/details', tags=["funnels"])
def get_funnels_with_details(projectId: int, rangeValue: str = None, startDate: int = None, endDate: int = None,
                             context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": funnels.get_by_user(project_id=projectId,
                                        user_id=context.user_id,
                                        range_value=rangeValue,
                                        start_date=startDate,
                                        end_date=endDate,
                                        details=True)}


@app.get('/{projectId}/funnels/issue_types', tags=["funnels"])
def get_possible_issue_types(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": funnels.get_possible_issue_types(project_id=projectId)}


@app.get('/{projectId}/funnels/{funnelId}/insights', tags=["funnels"])
def get_funnel_insights(projectId: int, funnelId: int, rangeValue: str = None, startDate: int = None,
                        endDate: int = None, context: schemas.CurrentContext = Depends(OR_context)):
    return funnels.get_top_insights(funnel_id=funnelId, project_id=projectId,
                                    range_value=rangeValue,
                                    start_date=startDate,
                                    end_date=endDate)


@app.post('/{projectId}/funnels/{funnelId}/insights', tags=["funnels"])
@app.put('/{projectId}/funnels/{funnelId}/insights', tags=["funnels"])
def get_funnel_insights_on_the_fly(projectId: int, funnelId: int, data: schemas.SessionsSearchPayloadSchema = Body(...),
                                   context: schemas.CurrentContext = Depends(OR_context)):
    return funnels.get_top_insights_on_the_fly(funnel_id=funnelId, project_id=projectId, data=data.dict())


@app.get('/{projectId}/funnels/{funnelId}/issues', tags=["funnels"])
def get_funnel_issues(projectId: int, funnelId, rangeValue: str = None, startDate: int = None, endDate: int = None,
                      context: schemas.CurrentContext = Depends(OR_context)):
    return funnels.get_issues(funnel_id=funnelId, project_id=projectId,
                              range_value=rangeValue,
                              start_date=startDate, end_date=endDate)


@app.post('/{projectId}/funnels/{funnelId}/issues', tags=["funnels"])
@app.put('/{projectId}/funnels/{funnelId}/issues', tags=["funnels"])
def get_funnel_issues_on_the_fly(projectId: int, funnelId: int, data: schemas.FunnelSchema = Body(...),
                                 context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": funnels.get_issues_on_the_fly(funnel_id=funnelId, project_id=projectId, data=data)}


@app.get('/{projectId}/funnels/{funnelId}/sessions', tags=["funnels"])
def get_funnel_sessions(projectId: int, funnelId: int, rangeValue: str = None, startDate: int = None,
                        endDate: int = None, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": funnels.get_sessions(funnel_id=funnelId, user_id=context.user_id, project_id=projectId,
                                         range_value=rangeValue,
                                         start_date=startDate,
                                         end_date=endDate)}


@app.post('/{projectId}/funnels/{funnelId}/sessions', tags=["funnels"])
@app.put('/{projectId}/funnels/{funnelId}/sessions', tags=["funnels"])
def get_funnel_sessions_on_the_fly(projectId: int, funnelId: int, data: schemas.FunnelSchema = Body(...),
                                   context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": funnels.get_sessions_on_the_fly(funnel_id=funnelId, user_id=context.user_id, project_id=projectId,
                                                    data=data.dict())}


@app.get('/{projectId}/funnels/issues/{issueId}/sessions', tags=["funnels"])
def get_issue_sessions(projectId: int, issueId: int, startDate: int = None, endDate: int = None,
                       context: schemas.CurrentContext = Depends(OR_context)):
    issue = issues.get(project_id=projectId, issue_id=issueId)
    return {
        "data": {"sessions": sessions.search_by_issue(user_id=context.user_id, project_id=projectId, issue=issue,
                                                      start_date=startDate,
                                                      end_date=endDate),
                 "issue": issue}}


@app.post('/{projectId}/funnels/{funnelId}/issues/{issueId}/sessions', tags=["funnels"])
@app.put('/{projectId}/funnels/{funnelId}/issues/{issueId}/sessions', tags=["funnels"])
def get_funnel_issue_sessions(projectId: int, funnelId: int, issueId: int, data: schemas.FunnelSchema = Body(...),
                              context: schemas.CurrentContext = Depends(OR_context)):
    data = funnels.search_by_issue(project_id=projectId, user_id=context.user_id, issue_id=issueId,
                                   funnel_id=funnelId, data=data.dict())
    if "errors" in data:
        return data
    if data.get("issue") is None:
        data["issue"] = issues.get(project_id=projectId, issue_id=issueId)
    return {
        "data": data
    }


@app.get('/{projectId}/funnels/{funnelId}', tags=["funnels"])
def get_funnel(projectId: int, funnelId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = funnels.get(funnel_id=funnelId, project_id=projectId)
    if data is None:
        return {"errors": ["funnel not found"]}
    return data


@app.post('/{projectId}/funnels/{funnelId}', tags=["funnels"])
@app.put('/{projectId}/funnels/{funnelId}', tags=["funnels"])
def edit_funnel(projectId: int, funnelId: int, data: schemas.FunnelSchema = Body(...),
                context: schemas.CurrentContext = Depends(OR_context)):
    return funnels.update(funnel_id=funnelId,
                          user_id=context.user_id,
                          name=data.name,
                          filter=data.filter,
                          is_public=data.is_public)


@app.delete('/{projectId}/funnels/{funnelId}', tags=["funnels"])
def delete_filter(projectId: int, funnelId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return funnels.delete(user_id=context.user_id, funnel_id=funnelId, project_id=projectId)


@app_apikey.put('/{projectKey}/sourcemaps', tags=["sourcemaps"])
def sign_sourcemap_for_upload(projectKey: str, data: schemas.SourcemapUploadPayloadSchema = Body(...),
                              context: schemas.CurrentContext = Depends(OR_context)):
    project_id = projects.get_internal_project_id(projectKey)
    if project_id is None:
        return {"errors": ["Project not found."]}

    return {"data": sourcemaps.presign_upload_urls(project_id=project_id, urls=data.urls)}


@app.get('/config/weekly_report', tags=["weekly report config"])
def get_weekly_report_config(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": weekly_report.get_config(user_id=context.user_id)}


@app.post('/config/weekly_report', tags=["weekly report config"])
@app.put('/config/weekly_report', tags=["weekly report config"])
def edit_weekly_report_config(data: schemas.WeeklyReportConfigSchema = Body(...),
                              context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": weekly_report.edit_config(user_id=context.user_id, weekly_report=data.weekly_report)}


@app.get('/{projectId}/issue_types', tags=["issues"])
def issue_types(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": issues.get_all_types()}


@app.get('/issue_types', tags=["issues"])
def all_issue_types(context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": issues.get_all_types()}


@app.get('/{projectId}/assist/sessions', tags=["assist"])
def sessions_live(projectId: int, context: schemas.CurrentContext = Depends(OR_context)):
    data = assist.get_live_sessions(projectId)
    return {'data': data}


@app.post('/{projectId}/assist/sessions', tags=["assist"])
def sessions_live_search(projectId: int, data: schemas.AssistSearchPayloadSchema = Body(...),
                         context: schemas.CurrentContext = Depends(OR_context)):
    data = assist.get_live_sessions(projectId, filters=data.filters)
    return {'data': data}


@app.post('/{projectId}/heatmaps/url', tags=["heatmaps"])
def get_heatmaps_by_url(projectId: int, data: schemas.GetHeatmapPayloadSchema = Body(...),
                        context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": heatmaps.get_by_url(project_id=projectId, data=data.dict())}


@public_app.get('/general_stats', tags=["private"], include_in_schema=False)
def get_general_stats():
    return {"data": {"sessions:": sessions.count_all()}}


@app.post('/{projectId}/mobile/{sessionId}/urls', tags=['mobile'])
def mobile_signe(projectId: int, sessionId: int, data: schemas.MobileSignPayloadSchema = Body(...),
                 context: schemas.CurrentContext = Depends(OR_context)):
    return {"data": mobile.sign_keys(project_id=projectId, session_id=sessionId, keys=data.keys)}