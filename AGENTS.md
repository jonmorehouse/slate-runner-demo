# Background

## Goals

## Slides

### Infra Agent

We want to show an agent that is running (in go), that is doing reconciliation, and running jobs. This agent should be 
connected and expose a set of commands, and operations it can do to add or remove state.

### Agent Controls

There should be an easy way to control the agent - such as locking it, putting it into read-only mode and things like 
that. There should be clear controls in the dashboard control plane that show it.

### Moving Orchestration Around

We really want to show that the agent can run _anywhere_ such as on an ec2 volume or something like that. All it's doing 
is talking home to the api to ask what it should do.

### Reconciliation Loop

The way the agent should check in with home is using a loop that runs and looks for jobs. All the state of the jobs 
should live in the s3 bucket backing the runner.

### Online / Offline Semantics

There should be online/offline semantics, meaning that a runner can be online/offline. If it goes offline for whatever 
reason, we should show that immediately, in almost real time.

## Demo

### Runner / Agent

1. Basic Agent that is connected and writes. This should run in a go application using an FX loop, and phone home for 
   jobs.

### Control-Plane App

1. Show a control plane for different applications
2. Sync State between runner and control plane.
3. Show a visualization of jobs and things.

### Infra Jobs

1. Run Terraform
2. Introspect State (Run a Terraform Refresh)
3. Show State and Sync It

## Tech Stack

### Backend

This should be a very simple python app that is backed by S3. It should use the slatedb bindings for python.

There are two s3 buckets that it will use:

1. the metainformation bucket - this stores all the agents, and things like health-checks and what not for each.
1. the runner bucket - it should have a way to see a bucket that is shared with a runner.

### UI

The backend python app should essentially be a full stack app with HTMX views, so we can display things. Let's pick a 
nice style to show some capabilities

### Runner

The runner should be a python based application that uses uber-fx. It should use a reconciliation type approach to 
communicate with the backend. It will write all of it's state locally into an s3 bucket, and respond to different 
commands.

By default, it will have several operating loops:

1. Health Checks - just run a health check and check in with the backend.
1. Operations - look for things like pause/unpause and read-only mode from the backend and reconcile that state.
1. Terraform - run a terraform job, to apply some infrastructure or do a plan-only mode or look for drift.
1. Send State - it should be able to send state home. 

The loops should all poll endpoints on the API, and check for jobs every 5 seconds. All state should be stored using s3 
and slate.

## Dev Env

### Buckets

We will use tigris for both buckets. They should be separate env-vars. Please update the README with the correct 
directions for each.
