# Engram API Integration Test Flow (PowerShell)

$BaseUrl = "http://localhost:8000"
$SourceAgentId = [Guid]::NewGuid().ToString()
$TargetAgentId = [Guid]::NewGuid().ToString()

write-host "--- Engram Integration Test (curl/PS) ---" -ForegroundColor Cyan

# 1. Register Source Agent
write-host "1. Registering Source Agent ($SourceAgentId)..."
$SourceAgent = @{
    agent_id = $SourceAgentId
    name = "PS Source Agent"
    endpoint_url = "http://localhost:9000"
    supported_protocols = @("A2A")
}
$Resp1 = Invoke-RestMethod -Uri "$BaseUrl/api/v1/register" -Method Post -Body ($SourceAgent | ConvertTo-Json) -ContentType "application/json"
write-host "   Success: $($Resp1.name)"

# 2. Register Target Agent
write-host "2. Registering Target Agent ($TargetAgentId)..."
$TargetAgent = @{
    agent_id = $TargetAgentId
    name = "PS Target Agent"
    endpoint_url = "http://localhost:9001"
    supported_protocols = @("MCP")
}
$Resp2 = Invoke-RestMethod -Uri "$BaseUrl/api/v1/register" -Method Post -Body ($TargetAgent | ConvertTo-Json) -ContentType "application/json"
write-host "   Success: $($Resp2.name)"

# 3. Enqueue Task
write-host "3. Enqueuing Translation (A2A -> MCP)..."
$Task = @{
    source_message = @{
        payload = @{
            intent = "fetch_status"
        }
        data = @{
            task = "status_check"
        }
    }
    source_protocol = "A2A"
    target_protocol = "MCP"
    target_agent_id = $TargetAgentId
}
$Resp3 = Invoke-RestMethod -Uri "$BaseUrl/api/v1/queue/enqueue" -Method Post -Body ($Task | ConvertTo-Json) -ContentType "application/json"
$TaskId = $Resp3.task_id
write-host "   Task Enqueued: $TaskId"

# 4. Poll for Message
write-host "4. Polling for results (may take a few seconds)..."
$MaxRetries = 5
$Message = $null
for ($i = 0; $i -lt $MaxRetries; $i++) {
    try {
        $Message = Invoke-RestMethod -Uri "$BaseUrl/api/v1/agents/$TargetAgentId/messages/poll" -Method Post
        if ($Message) { break }
    } catch {
        # Likely 204 or other non-content response
    }
    write-host "   Waiting... ($($i+1)/$MaxRetries)"
    Start-Sleep -Seconds 2
}

if ($Message) {
    write-host "SUCCESS: Received Translated Message!" -ForegroundColor Green
    write-host ($Message.payload | ConvertTo-Json -Depth 5)
    
    # 5. Acknowledge
    $MsgId = $Message.message_id
    Invoke-RestMethod -Uri "$BaseUrl/api/v1/agents/messages/$MsgId/ack" -Method Post
    write-host "5. Message $MsgId acknowledged."
} else {
    write-host "FAILED: Timeout waiting for message." -ForegroundColor Red
}
