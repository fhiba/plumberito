import json
import os

import pulumi
import pulumi.automation as auto
import pulumi_gcp as gcp

GCP_PROJECT = os.environ.get("GCP_PROJECT", "")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")


def _create_cloud_run(name: str, config: dict):
    image = config.get("image", "us-docker.pkg.dev/cloudrun/container/hello")
    port = config.get("port", 8080)
    memory = config.get("memory", "512Mi")
    cpu = config.get("cpu", "1")
    env_vars = config.get("env_vars", {})
    allow_unauthenticated = config.get("allow_unauthenticated", True)

    env_list = [{"name": k, "value": v} for k, v in env_vars.items()]

    container = {
        "image": image,
        "ports": {"container_port": port},
        "resources": {"limits": {"memory": memory, "cpu": cpu}},
    }
    if env_list:
        container["envs"] = env_list

    service = gcp.cloudrunv2.Service(
        name,
        name=name,
        location=GCP_REGION,
        ingress="INGRESS_TRAFFIC_ALL",
        deletion_protection=False,
        template={"containers": [container]},
    )

    if allow_unauthenticated:
        gcp.cloudrunv2.ServiceIamMember(
            f"{name}-public",
            name=service.name,
            location=GCP_REGION,
            role="roles/run.invoker",
            member="allUsers",
        )

    pulumi.export(f"{name}_url", service.uri)
    pulumi.export(f"{name}_name", service.name)


def _create_bucket(name: str, config: dict):
    location = config.get("location", "US")

    bucket = gcp.storage.Bucket(
        name,
        name=f"{GCP_PROJECT}-{name}",
        location=location,
        uniform_bucket_level_access=True,
    )

    pulumi.export(f"{name}_name", bucket.name)
    pulumi.export(f"{name}_url", bucket.url)


RESOURCE_BUILDERS = {
    "cloud_run_service": _create_cloud_run,
    "cloud_storage_bucket": _create_bucket,
}


def _provision_infrastructure(project_name: str, resources: list) -> str:
    def pulumi_program():
        for res in resources:
            res_type = res.get("type", "")
            res_name = res.get("name", "")
            res_config = res.get("config", {})

            builder = RESOURCE_BUILDERS.get(res_type)
            if builder:
                builder(res_name, res_config)

    try:
        stack = auto.create_or_select_stack(
            stack_name="dev",
            project_name=project_name,
            program=pulumi_program,
        )

        stack.set_config("gcp:project", auto.ConfigValue(value=GCP_PROJECT))
        stack.set_config("gcp:region", auto.ConfigValue(value=GCP_REGION))

        result = stack.up(on_output=print)

        outputs = {k: v.value for k, v in result.outputs.items()}
        resource_changes = result.summary.resource_changes or {}

        return json.dumps({
            "status": "success",
            "outputs": outputs,
            "summary": {
                "created": resource_changes.get("create", 0),
                "updated": resource_changes.get("update", 0),
                "unchanged": resource_changes.get("same", 0),
            },
        })
    except auto.StackAlreadyExistsError:
        return json.dumps({"status": "error", "message": f"Stack '{project_name}' already exists. Use a different project_name or destroy the existing one first."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def _destroy_infrastructure(project_name: str) -> str:
    def empty_program():
        pass

    try:
        stack = auto.select_stack(
            stack_name="dev",
            project_name=project_name,
            program=empty_program,
        )

        stack.set_config("gcp:project", auto.ConfigValue(value=GCP_PROJECT))
        stack.set_config("gcp:region", auto.ConfigValue(value=GCP_REGION))

        stack.destroy(on_output=print)
        stack.workspace.remove_stack("dev")

        return json.dumps({"status": "success", "message": f"Infrastructure for '{project_name}' destroyed."})
    except auto.errors.StackNotFoundError:
        return json.dumps({"status": "error", "message": f"Stack '{project_name}' not found."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
