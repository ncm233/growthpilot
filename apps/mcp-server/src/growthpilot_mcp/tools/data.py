from ..server import mcp


@mcp.tool
def fetch_growth_data(metric_name: str = "signup_conversion") -> dict:
    """拉取当前的转化漏斗、注册表单字段、CRM 客户分群、ERP 订单统计快照。

    只读工具，不会修改任何系统。数据源是 GrowthPilot 的 Mock/Real 双实现工具层
    （企业微信/飞书/CRM/ERP/表单/埋点），未配置真实密钥时返回确定性的合成数据。

    Args:
        metric_name: 关注的指标名，会传给埋点工具作为漏斗查询的种子（同一个
            metric_name 每次返回相同的合成漏斗，方便复现）。

    Returns:
        {"funnel": [...], "form_fields": [...], "segments": [...], "erp": {...}}
    """
    from app.agents import data_agent
    from app.tools import get_analytics_tool, get_crm_tool, get_erp_tool, get_form_tool

    tools = {
        "analytics": get_analytics_tool(),
        "form": get_form_tool(),
        "crm": get_crm_tool(),
        "erp": get_erp_tool(),
    }
    return data_agent.gather(metric_name, tools)
