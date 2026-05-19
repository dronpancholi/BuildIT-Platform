import asyncio
import sys

from temporalio.client import Client

async def main():
    try:
        client = await Client.connect("localhost:7233", namespace="default")
        print("Connected to Temporal.")
        
        # We only want to terminate the "queue-pressure-*" workflows that are running
        query = "WorkflowType = 'ReportGenerationWorkflow' AND ExecutionStatus = 'Running'"
        
        count = 0
        async for workflow in client.list_workflows(query=query):
            if "queue-pressure" in workflow.id:
                try:
                    handle = client.get_workflow_handle(workflow.id, run_id=workflow.run_id)
                    await handle.terminate("Cleanup of stuck stress test workflows")
                    count += 1
                    if count % 100 == 0:
                        print(f"Terminated {count} workflows...")
                except Exception as e:
                    print(f"Failed to terminate {workflow.id}: {e}")
                    
        print(f"Successfully terminated {count} stress test workflows.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
