from langfuse import observe


@observe(as_type="tool")
def gather(metric_name: str, tools: dict) -> dict:
    """Calls the MCP-style tool layer and returns raw structured data.
    Nothing here is narrated or interpreted — that's Opportunity/Experiment Agent's
    job. Keeping fetch and interpretation separate is what lets Critic Agent check
    the interpretation against the fetch results afterwards."""
    return {
        "funnel": tools["analytics"].get_funnel(metric_name),
        "form_fields": tools["form"].get_fields("signup_form"),
        "segments": tools["crm"].get_segments(),
        "erp": tools["erp"].get_order_stats(),
    }
