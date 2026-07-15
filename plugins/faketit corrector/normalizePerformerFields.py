import json
import sys
import urllib.request


def output(data=None, error=None):
    print(json.dumps({
        "output": data or {},
        **({"error": error} if error else {})
    }))


def graphql(url, query, variables=None, cookie=None):
    body = json.dumps({
        "query": query,
        "variables": variables or {}
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if cookie:
        headers["Cookie"] = cookie

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"]))

    return data["data"]


def get_cookie(server):
    session_cookie = server.get("SessionCookie") or {}

    if session_cookie.get("Name") and session_cookie.get("Value"):
        return f'{session_cookie["Name"]}={session_cookie["Value"]}'

    return None


def update_performer_fake_tits(gql_url, performer_id, preferred, cookie=None):
    mutation = """
    mutation PerformerUpdate($input: PerformerUpdateInput!) {
      performerUpdate(input: $input) {
        id
        name
        fake_tits
      }
    }
    """

    return graphql(
        gql_url,
        mutation,
        {
            "input": {
                "id": performer_id,
                "fake_tits": preferred
            }
        },
        cookie
    )["performerUpdate"]

def update_performer_ethnicity(gql_url, performer_id, ethnicity, cookie=None):
    mutation = """
    mutation PerformerUpdate($input: PerformerUpdateInput!) {
      performerUpdate(input: $input) {
        id
        name
        ethnicity
      }
    }
    """

    return graphql(
        gql_url,
        mutation,
        {
            "input": {
                "id": performer_id,
                "ethnicity": ethnicity
            }
        },
        cookie
    )["performerUpdate"]

def normalize_performer(gql_url, performer, preferred, from_values, cookie=None):
    current = performer.get("fake_tits")

    if current not in from_values:
        return False

    updated = update_performer_fake_tits(
        gql_url,
        performer["id"],
        preferred,
        cookie
    )

    return updated.get("fake_tits") == preferred


def run_task(gql_url, preferred, from_values, cookie=None):
    query = """
    query AllPerformers($page: Int!, $per_page: Int!) {
      findPerformers(
        performer_filter: {}
        filter: { page: $page, per_page: $per_page }
      ) {
        count
        performers {
          id
          name
          fake_tits
          ethnicity
        }
      }
    }
    """

    page = 1
    per_page = 500

    checked = 0
    matched = 0
    changed = 0
    failed = 0

    while True:
        result = graphql(
            gql_url,
            query,
            {
                "page": page,
                "per_page": per_page
            },
            cookie=cookie
        )["findPerformers"]

        performers = result["performers"]

        if not performers:
            break

        for performer in performers:
            checked += 1

            # Normalize ethnicity independently of the fake_tits value.
            if performer.get("ethnicity") == "Caucasian":
                update_performer_ethnicity(
                    gql_url,
                    performer["id"],
                    "White",
                    cookie
                )

            current = performer.get("fake_tits")

            if current not in from_values:
                continue

            matched += 1

            updated = update_performer_fake_tits(
                gql_url,
                performer["id"],
                preferred,
                cookie
            )

            new_value = updated.get("fake_tits")

            if new_value == preferred:
                changed += 1
            else:
                failed += 1
        if len(performers) < per_page:
            break

        page += 1

    output({
        "mode": "task",
        "checked": checked,
        "matched": matched,
        "changed": changed,
        "failed": failed,
        "preferred": preferred,
        "fromValues": sorted(from_values)
    })


def run_hook(gql_url, hook_context, preferred, from_values, cookie=None):
    performer_id = hook_context.get("id")

    if not performer_id:
        output({
            "mode": "hook",
            "skipped": True,
            "reason": "No performer id in hookContext"
        })
        return

    query = """
    query FindPerformer($id: ID!) {
      findPerformer(id: $id) {
        id
        name
        fake_tits
        ethnicity
      }
    }
    """

    performer = graphql(
        gql_url,
        query,
        {"id": performer_id},
        cookie
    )["findPerformer"]

    if not performer:
        output({
            "mode": "hook",
            "skipped": True,
            "reason": "Performer not found",
            "id": performer_id
        })
        return

    original_value = performer.get("fake_tits")

    changed = normalize_performer(
        gql_url,
        performer,
        preferred,
        from_values,
        cookie
    )

    if performer.get("ethnicity") == "Caucasian":
        update_performer_ethnicity(
            gql_url,
            performer["id"],
            "White",
            cookie
        )

    output({
        "mode": "hook",
        "changed": changed,
        "id": performer_id,
        "name": performer.get("name"),
        "from": original_value,
        "to": preferred if changed else original_value
    })


def main():
    plugin_input = json.load(sys.stdin)

    args = plugin_input.get("args", {})

    preferred = args.get("preferredValue", "Na")

    from_values_raw = args.get("fromValues", "Natural,NA,N/A")
    from_values = {
        v.strip() for v in from_values_raw.split(",") if v.strip()
    }

    server = plugin_input.get("server_connection") or {}

    scheme = server.get("Scheme", "http")
    port = server.get("Port")

    if not port:
        output(error="No Stash server port found in server_connection")
        sys.exit(1)

    gql_url = f"{scheme}://localhost:{port}/graphql"

    cookie = get_cookie(server)

    hook_context = args.get("hookContext")

    if hook_context:
        run_hook(
            gql_url,
            hook_context,
            preferred,
            from_values,
            cookie
        )
    else:
        run_task(
            gql_url,
            preferred,
            from_values,
            cookie
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        output(error=str(e))
        sys.exit(1)