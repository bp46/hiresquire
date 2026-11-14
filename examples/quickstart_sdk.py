"""End-to-end HireSquire SDK quickstart example."""

import os

from hiresquire import HireSquireClient


def main() -> None:
    token = os.environ["HIRESQUIRE_API_TOKEN"]
    with HireSquireClient(token) as client:
        me = client.whoami()
        print(f"Signed in as {me['user']['name']} | Balance: {me['credits']['formatted_balance']}")

        job = client.jobs.create(
            title="Senior Python Engineer",
            description=(
                "We are looking for a Senior Python Engineer with 5+ years building "
                "APIs with FastAPI, PostgreSQL, and distributed task queues."
            ),
            resumes=[
                {
                    "filename": "ada_lovelace.txt",
                    "content": (
                        "Ada Lovelace — Senior Python Engineer with 8 years of experience "
                        "building FastAPI services, PostgreSQL pipelines, and async workers."
                    ),
                }
            ],
            leniency_level=6,
        )
        print(f"Submitted job #{job['job_id']} ({job['status']})")

        results = client.jobs.wait(job["job_id"])
        for candidate in results["candidates"]:
            print(f"- {candidate['name']}: {candidate['score']}/100")


if __name__ == "__main__":
    main()
