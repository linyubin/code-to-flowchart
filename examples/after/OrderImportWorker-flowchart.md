# Flowchart: OrderImportWorker.ProcessNextBatch (example)

Traced from [`examples/before/OrderImportWorker.cs`](../before/OrderImportWorker.cs) — a fictional but representative "god method": a self-re-arming polling timer whose handler has a device-connectivity check, a presence check, and a format-branch duplication (new vs. legacy order format) that mirror the same shape you'll find in most legacy polling services, regardless of language or domain.

**Note on scope:** the real source wraps nearly every statement in its own `try/catch` that only logs and falls through. Those are omitted below — they don't change the control flow shown here. The outer method-level `try/finally` always restarts the poll timer regardless of which path was taken; that's the shared `Finally` node every path flows into.

**Why two near-identical subgraphs:** the New-format and Old-format branches mirror each other step for step but differ in field lists and insert defaults — the exact kind of structural duplication this skill is built to make visible.

```mermaid
flowchart TD
    Start(["Timer elapses (every 1s)"]) --> StopTimer["Stop polling timer"]
    StopTimer --> FetchConfig["Fetch watcher config from DB by name"]
    FetchConfig --> CheckPing{"Watcher ping successful?"}
    CheckPing -->|No| Finally
    CheckPing -->|Yes| HasConfig{"Watcher config found?"}
    HasConfig -->|No| Finally
    HasConfig -->|Yes| Connect["Connect to file watcher"]
    Connect --> IsConnected{"Watcher connected?"}
    IsConnected -->|No| Finally
    IsConnected -->|Yes| ReadFlag1["Read 'new file available' flag"]
    ReadFlag1 --> FilePresent{"New file present?"}

    FilePresent -->|No| ReadProcessed1["Read 'order processed' flag"]
    ReadProcessed1 --> ProcTrue1{"Processed flag = True?"}
    ProcTrue1 -->|Yes| ResetFlag["Write processed flag = False"]
    ProcTrue1 -->|No| NoAction1["No action - already reset"]
    ResetFlag --> Finally
    NoAction1 --> Finally

    FilePresent -->|Yes| ReadLine["Read raw order line"]
    ReadLine --> Format{"Line length?"}

    subgraph New["New / extended format path (length > 25)"]
        Format -->|"> 25 chars"| ParseNew["Split line into 6 fields: orderId / customerId / qty / date / reference / batch"]
        ParseNew --> LookupNew["Generate import batch ID, look up existing order by orderId"]
        LookupNew --> FoundNew{"Order already exists?"}
        FoundNew -->|No| InsertNew["Insert new order row - status PENDING"]
        FoundNew -->|Yes| ReadProcNew["Read processed flag"]
        ReadProcNew --> ProcFalseNew{"Processed = False?"}
        ProcFalseNew -->|No| SkipNew["No action - already processed"]
        ProcFalseNew -->|Yes| ImportGenNew{"Import already generated?"}
        ImportGenNew -->|Yes| SkipNew2["No action - already generated"]
        ImportGenNew -->|No| LookupCustomer["Look up customer profile by customerId"]
        LookupCustomer --> UpdateNew["Update order row: customer/qty/batch, status COMPLETE"]
        UpdateNew --> WriteProcNew["Write processed flag = True"]
    end

    subgraph Old["Old / legacy format path (length < 25)"]
        Format -->|"< 25 chars"| LookupOld["Generate import batch ID, look up existing order by raw line"]
        LookupOld --> FoundOld{"Order already exists?"}
        FoundOld -->|No| InsertOld["Insert new order row - status COMPLETE, placeholder customer UNKNOWN / legacy-import / GEN"]
        FoundOld -->|Yes| ReadProcOld["Read processed flag"]
        ReadProcOld --> ProcFalseOld{"Processed = False?"}
        ProcFalseOld -->|No| SkipOld["No action - already processed"]
        ProcFalseOld -->|Yes| ImportGenOld{"Import already generated?"}
        ImportGenOld -->|Yes| SkipOld2["No action - already generated"]
        ImportGenOld -->|No| UpdateOld["Update order row: import batch ID only"]
        UpdateOld --> WriteProcOld["Write processed flag = True"]
    end

    InsertNew --> Finally
    SkipNew --> Finally
    SkipNew2 --> Finally
    WriteProcNew --> Finally
    InsertOld --> Finally
    SkipOld --> Finally
    SkipOld2 --> Finally
    WriteProcOld --> Finally

    Finally(["Restart poll timer (always runs)"])

    classDef noAction fill:#552222,stroke:#ff6666,color:#fff
    class NoAction1,SkipNew,SkipNew2,SkipOld,SkipOld2 noAction
```
