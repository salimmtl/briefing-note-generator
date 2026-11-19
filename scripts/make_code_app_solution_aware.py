"""Make a pushed code app solution-aware and add it to the solution (Power Apps makeSolutionAware API).

`pac code push --solutionName` creates the app outside Dataverse in some environments (almMode "Environment"),
so it never appears in the solution. This calls the same API the npm Power Apps CLI uses
(`pa app push --solution-id`), with a token from a COPY of the PAC CLI token cache (the cache is never modified).

Usage: python scripts/make_code_app_solution_aware.py <appId>
"""

import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request

import msal
from msal_extensions import FilePersistenceWithDataProtection, PersistedTokenCache

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dv_api import get, q  # noqa: E402

PAC_CLIENT = "9cee029c-6210-4654-90bb-17e6e9d36617"  # Power Platform CLI public client


def pac_token(tenant, username, scope):
    src = os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "PowerAppsCli", "tokencache_msalv3.dat")
    copy = os.path.join(tempfile.mkdtemp(), "cache.dat")
    shutil.copyfile(src, copy)
    try:
        cache = PersistedTokenCache(FilePersistenceWithDataProtection(copy))
        app = msal.PublicClientApplication(PAC_CLIENT, authority=f"https://login.windows.net/{tenant}", token_cache=cache)
        account = next(a for a in app.get_accounts() if a["username"].lower() == username.lower())
        result = app.acquire_token_silent([scope], account=account)
        if not result or "access_token" not in result:
            raise SystemExit(f"[FAIL] no cached PAC token for {username}: run 'pac auth create' first")
        return result["access_token"]
    finally:
        shutil.rmtree(os.path.dirname(copy), ignore_errors=True)


def main():
    app_id = sys.argv[1]
    tenant = os.environ["TENANT_ID"]
    who = get("WhoAmI")
    user = get(f"systemusers({who['UserId']})?$select=domainname")["domainname"]
    org = get(f"organizations({who['OrganizationId']})?$select=name")
    sol = get(f"solutions?$select=solutionid&$filter={q(chr(39).join(['uniquename eq ', os.environ['SOLUTION_NAME'], '']))}")
    solution_id = sol["value"][0]["solutionid"]
    env_id = os.environ.get("ENVIRONMENT_ID") or sys.argv[2]
    host = env_id.replace("-", "")
    endpoint = f"https://{host[:-2]}.{host[-2:]}.environment.api.powerplatform.com"
    token = pac_token(tenant, user, "https://api.powerplatform.com/.default")
    req = urllib.request.Request(f"{endpoint}/powerapps/apps/{app_id}/makeSolutionAware?api-version=1",
                                 data=json.dumps({"solutionId": solution_id}).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            print(f"[OK]   {app_id} is solution-aware in {os.environ['SOLUTION_NAME']} ({org['name']}): HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"[FAIL] makeSolutionAware: HTTP {e.code} {e.read()[:500]}")


if __name__ == "__main__":
    main()
