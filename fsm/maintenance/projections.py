from fsm.maintenance.engine import project_job_completion


def on_service_job_update(doc, method=None):
	project_job_completion(doc)
