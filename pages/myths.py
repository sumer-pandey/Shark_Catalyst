# pages/myths.py
import streamlit as st
from utils import cached_query, format_currency
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")

# --- Deterministic myth list (20 items). Money columns are IN LAKHS in dataset. ---
MYTHS = [
    {
        "id": "myth01",
        "title": "Majority of on-air pitches actually close (invested)",
        "context": "Closure rate = closed deals / on-air deals. Closed means invested_amount IS NOT NULL.",
        "check_sql": """
            SELECT
              COUNT(*) AS total_onair,
              SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS closed_deals,
              CAST(SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(COUNT(*),0) AS closure_rate
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN invested_amount IS NOT NULL THEN 'Closed' ELSE 'Not closed' END AS status,
                      COUNT(*) AS cnt
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN invested_amount IS NOT NULL THEN 'Closed' ELSE 'Not closed' END;
        """,
        "explainer": "Closure rate is the share of on-air pitches that resulted in investments. (Amounts in this dataset are in lakhs.)",
        "explorer_prefill": {}
    },
        {
        "id": "myth02",
        "title": "Most funded deals are equity-only (no royalty)",
        "context": "Compare counts of equity-only funded deals (no royalty) vs funded deals with royalty.",
        "check_sql": """
            SELECT
              SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS total_funded,
              SUM(CASE WHEN invested_amount IS NOT NULL AND COALESCE(royalty_percentage,0)=0 THEN 1 ELSE 0 END) AS equity_only_funded,
              CAST(SUM(CASE WHEN invested_amount IS NOT NULL AND COALESCE(royalty_percentage,0)=0 THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END),0) AS equity_only_share_among_funded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN invested_amount IS NULL THEN 'Unknown'
                         WHEN COALESCE(royalty_percentage,0) > 0 THEN 'Royalty'
                         ELSE 'Equity-only' END AS instrument,
                      COUNT(*) AS pitches
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN invested_amount IS NULL THEN 'Unknown'
                         WHEN COALESCE(royalty_percentage,0) > 0 THEN 'Royalty'
                         ELSE 'Equity-only' END;
        """,
        "verdict_rule": "True if equity_only_share_among_funded > 0.50 (i.e., >50% of funded deals are equity-only).",
        "explainer": "If True: most funding on the show comes as straight equity (no royalty), implying investors prefer ownership deals. If False: royalty deals are common.",
        "explorer_prefill": {}
    },

    {
        "id": "myth03",
        "title": "Majority of funded deals are under ₹1 crore (i.e., invested_amount < 100 lakhs)",
        "context": "Check proportion of funded deals with invested_amount < 100. (invested_amount is IN LAKHS).",
        "check_sql": """
            SELECT
              SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS total_funded,
              SUM(CASE WHEN invested_amount IS NOT NULL AND invested_amount < 100 THEN 1 ELSE 0 END) AS funded_under_1cr,
              CAST(SUM(CASE WHEN invested_amount IS NOT NULL AND invested_amount < 100 THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END),0) AS pct_under_1cr
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN invested_amount IS NULL THEN 'Unknown'
                         WHEN invested_amount < 100 THEN '<1 Cr'
                         WHEN invested_amount BETWEEN 100 AND 499 THEN '1-5 Cr'
                         ELSE '5+ Cr' END AS bucket,
                      COUNT(*) AS cnt
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN invested_amount IS NULL THEN 'Unknown'
                         WHEN invested_amount < 100 THEN '<1 Cr'
                         WHEN invested_amount BETWEEN 100 AND 499 THEN '1-5 Cr'
                         ELSE '5+ Cr' END;
        """,
        "explainer": "Shows distribution of funded check sizes (buckets are in lakhs; 100 lakhs = 1 Cr).",
        "explorer_prefill": {}
    },

    {
        "id": "myth04",
        "title": "Founders from metro cities have higher funded rates than non-metro founders",
        "context": "Join deals to dim_city (city_norm) and compare funded rates for metro vs non-metro.",
        "check_sql": """
            SELECT
            SUM(CASE WHEN dc.is_metro = TRUE THEN 1 ELSE 0 END) AS total_metro,
            SUM(CASE WHEN dc.is_metro = TRUE AND d.invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_metro,
            SUM(CASE WHEN dc.is_metro = FALSE OR dc.is_metro IS NULL THEN 1 ELSE 0 END) AS total_nonmetro,
            SUM(CASE WHEN (dc.is_metro = FALSE OR dc.is_metro IS NULL) AND d.invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_nonmetro,
            CAST(SUM(CASE WHEN dc.is_metro = TRUE AND d.invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN dc.is_metro = TRUE THEN 1 ELSE 0 END),0) AS funded_rate_metro,
            CAST(SUM(CASE WHEN (dc.is_metro = FALSE OR dc.is_metro IS NULL) AND d.invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN dc.is_metro = FALSE OR dc.is_metro IS NULL THEN 1 ELSE 0 END),0) AS funded_rate_nonmetro
            FROM public.deals d
            LEFT JOIN public.dim_city dc ON LOWER(TRIM(d.pitchers_city)) = dc.city_norm
            WHERE (%s = 'All' OR d.season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN dc.is_metro = TRUE THEN 'Metro' WHEN dc.is_metro = FALSE THEN 'Non-metro' ELSE 'Unknown' END AS city_type,
                    COUNT(*) AS pitches, SUM(CASE WHEN d.invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
            FROM public.deals d
            LEFT JOIN public.dim_city dc ON LOWER(TRIM(d.pitchers_city)) = dc.city_norm
            WHERE (%s = 'All' OR d.season = %s)
            GROUP BY CASE WHEN dc.is_metro = TRUE THEN 'Metro' WHEN dc.is_metro = FALSE THEN 'Non-metro' ELSE 'Unknown' END;
        """,
        "explainer": "Compares funded rates for metro and non-metro mapped cities (boolean is_metro in dim_city).",
        "explorer_prefill": {"city_type": "Metro"}
    },

    {
        "id": "myth05",
        "title": "Female-only teams are funded less often than male-only teams",
        "context": "Compare funded rates for female-only teams vs male-only teams (based on presenter counts).",
        "check_sql": """
            SELECT
              SUM(CASE WHEN female_presenters>0 AND male_presenters=0 THEN 1 ELSE 0 END) AS total_female_only,
              SUM(CASE WHEN female_presenters>0 AND male_presenters=0 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_female_only,
              SUM(CASE WHEN male_presenters>0 AND female_presenters=0 THEN 1 ELSE 0 END) AS total_male_only,
              SUM(CASE WHEN male_presenters>0 AND female_presenters=0 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_male_only,
              CAST(SUM(CASE WHEN female_presenters>0 AND male_presenters=0 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN female_presenters>0 AND male_presenters=0 THEN 1 ELSE 0 END),0) AS funded_rate_female_only,
              CAST(SUM(CASE WHEN male_presenters>0 AND female_presenters=0 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN male_presenters>0 AND female_presenters=0 THEN 1 ELSE 0 END),0) AS funded_rate_male_only
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN female_presenters>0 AND male_presenters=0 THEN 'Female-only'
                         WHEN male_presenters>0 AND female_presenters=0 THEN 'Male-only'
                         WHEN male_presenters>0 AND female_presenters>0 THEN 'Mixed'
                         ELSE 'Unknown' END AS group_label,
                      COUNT(*) AS pitches, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN female_presenters>0 AND male_presenters=0 THEN 'Female-only'
                         WHEN male_presenters>0 AND female_presenters=0 THEN 'Male-only'
                         WHEN male_presenters>0 AND female_presenters>0 THEN 'Mixed'
                         ELSE 'Unknown' END;
        """,
        "explainer": "Direct compare funded rates for female-only vs male-only presenting teams.",
        "explorer_prefill": {}
    },

        {
        "id": "myth06",
        "title": "Deals with multiple sharks have higher average investment",
        "context": "Compare average invested amount for deals with >1 shark vs single-shark deals.",
        "check_sql": """
            SELECT
              SUM(CASE WHEN Number_of_sharks_in_deal > 1 THEN 1 ELSE 0 END) AS total_multi,
              AVG(CASE WHEN Number_of_sharks_in_deal > 1 THEN NULLIF(invested_amount,0) END) AS avg_multi,
              SUM(CASE WHEN Number_of_sharks_in_deal = 1 THEN 1 ELSE 0 END) AS total_single,
              AVG(CASE WHEN Number_of_sharks_in_deal = 1 THEN NULLIF(invested_amount,0) END) AS avg_single
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN Number_of_sharks_in_deal > 1 THEN 'Multiple sharks' WHEN Number_of_sharks_in_deal = 1 THEN 'Single shark' ELSE 'Unknown' END AS shark_count,
                      COUNT(*) AS pitches, AVG(NULLIF(invested_amount,0)) AS avg_invested
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN Number_of_sharks_in_deal > 1 THEN 'Multiple sharks' WHEN Number_of_sharks_in_deal = 1 THEN 'Single shark' ELSE 'Unknown' END;
        """,
        "explainer": "Checks whether multi-shark (co-invested) deals have higher average invested_amount than single-shark deals (amounts are in lakhs).",
        "explorer_prefill": {}
    },

    {
        "id": "myth07",
        "title": "Most funded deals involve multiple sharks (co-investment)",
        "context": "Check whether >50% of funded deals had Number_of_sharks_in_deal > 1.",
        "check_sql": """
            SELECT
              SUM(CASE WHEN Number_of_sharks_in_deal > 1 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS multi_shark_funded,
              SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS total_funded,
              CAST(SUM(CASE WHEN Number_of_sharks_in_deal > 1 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END),0) AS pct_multi_shark
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN Number_of_sharks_in_deal > 1 THEN 'Multiple sharks' WHEN Number_of_sharks_in_deal = 1 THEN 'Single shark' ELSE 'Unknown' END AS shark_count,
                      COUNT(*) AS pitches, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN Number_of_sharks_in_deal > 1 THEN 'Multiple sharks' WHEN Number_of_sharks_in_deal = 1 THEN 'Single shark' ELSE 'Unknown' END;
        """,
        "explainer": "Determines if co-investments are the dominant outcome among funded deals.",
        "explorer_prefill": {}
    },

    {
        "id": "myth08",
        "title": "Sharks typically secure more equity than founders originally asked for",
        "context": "Compare avg(equity_final) vs avg(equity_asked).",
        "check_sql": """
            SELECT
              AVG(NULLIF(equity_asked,0)) AS avg_asked_equity,
              AVG(NULLIF(equity_final,0)) AS avg_final_equity
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT equity_asked, equity_final FROM public.deals
            WHERE equity_asked IS NOT NULL AND (%s = 'All' OR season = %s)
            ORDER BY equity_asked DESC
            LIMIT 200;
        """,
        "explainer": "If average final equity exceeds average asked equity, founders on average conceded more ownership.",
        "explorer_prefill": {}
    },

    {
        "id": "myth09",
        "title": "Final deal valuations are lower than founders' requested valuations",
        "context": "Compare average valuation_requested vs average Deal_Valuation (both in lakhs).",
        "check_sql": """
            SELECT
              AVG(NULLIF(valuation_requested,0)) AS avg_ask_valuation,
              AVG(NULLIF(deal_valuation,0)) AS avg_deal_valuation
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT asked_amount AS asked_lakhs, invested_amount AS invested_lakhs, equity_asked, equity_final
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            ORDER BY asked_amount DESC
            LIMIT 200;
        """,
        "explainer": "Checks whether deals implied valuations that are lower than founders' asks (values are in lakhs).",
        "explorer_prefill": {}
    },

    {
        "id": "myth10",
        "title": "Funded companies have higher monthly sales on average",
        "context": "Compare avg monthly_sales for funded vs not funded (monthly_sales raw value).",
        "check_sql": """
            SELECT
              AVG(NULLIF(monthly_sales,0)) AS avg_monthly_all,
              AVG(CASE WHEN invested_amount IS NOT NULL THEN NULLIF(monthly_sales,0) END) AS avg_monthly_funded,
              AVG(CASE WHEN invested_amount IS NULL THEN NULLIF(monthly_sales,0) END) AS avg_monthly_notfunded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN monthly_sales IS NULL THEN 'Unknown'
                       WHEN monthly_sales < 50000 THEN '<50k'
                       WHEN monthly_sales BETWEEN 50000 AND 199999 THEN '50k-2L'
                       WHEN monthly_sales BETWEEN 200000 AND 999999 THEN '2L-10L'
                       ELSE '10L+' END AS sales_bucket,
                      COUNT(*) AS pitches, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN monthly_sales IS NULL THEN 'Unknown'
                       WHEN monthly_sales < 50000 THEN '<50k'
                       WHEN monthly_sales BETWEEN 50000 AND 199999 THEN '50k-2L'
                       WHEN monthly_sales BETWEEN 200000 AND 999999 THEN '2L-10L'
                       ELSE '10L+' END;
        """,
        "explainer": "Checks whether funded startups show higher monthly sales on average (raw currency values).",
        "explorer_prefill": {}
    },

    {
        "id": "myth11",
        "title": "Startups with patents are funded at a higher rate",
        "context": "Compare funded rates where Has_Patents = 1 vs 0.",
        "check_sql": """
            SELECT
              SUM(CASE WHEN Has_Patents = TRUE THEN 1 ELSE 0 END) AS total_patent,
              SUM(CASE WHEN Has_Patents = TRUE AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_patent,
              SUM(CASE WHEN Has_Patents = FALSE THEN 1 ELSE 0 END) AS total_no_patent,
              SUM(CASE WHEN Has_Patents = FALSE AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_no_patent,
              CAST(SUM(CASE WHEN Has_Patents = TRUE AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN Has_Patents = TRUE THEN 1 ELSE 0 END),0) AS funded_rate_patent,
              CAST(SUM(CASE WHEN Has_Patents = FALSE AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN Has_Patents = FALSE THEN 1 ELSE 0 END),0) AS funded_rate_no_patent
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT COALESCE(CAST(Has_Patents AS VARCHAR(10)),'Unknown') AS has_patent, COUNT(*) AS pitches, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY COALESCE(CAST(Has_Patents AS VARCHAR(10)),'Unknown');
        """,
        "explainer": "Tests whether having patents correlates with higher funded rate.",
        "explorer_prefill": {}
    },

    {
        "id": "myth12",
        "title": "Startups with many SKUs (>20) are funded less often",
        "context": "Compare funded rate for SKUs > 20 vs <= 20 (or unknown).",
        "check_sql": """
            SELECT
              SUM(CASE WHEN SKUs > 20 THEN 1 ELSE 0 END) AS total_high_skus,
              SUM(CASE WHEN SKUs > 20 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_high_skus,
              SUM(CASE WHEN SKUs <= 20 OR SKUs IS NULL THEN 1 ELSE 0 END) AS total_low_skus,
              SUM(CASE WHEN (SKUs <= 20 OR SKUs IS NULL) AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_low_skus,
              CAST(SUM(CASE WHEN SKUs > 20 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN SKUs > 20 THEN 1 ELSE 0 END),0) AS funded_rate_high_skus,
              CAST(SUM(CASE WHEN (SKUs <= 20 OR SKUs IS NULL) AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN (SKUs <= 20 OR SKUs IS NULL) THEN 1 ELSE 0 END),0) AS funded_rate_low_skus
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN SKUs IS NULL THEN 'Unknown' WHEN SKUs < 5 THEN '<5' WHEN SKUs BETWEEN 5 AND 20 THEN '5-20' ELSE '20+' END AS skus_bucket,
                      COUNT(*) AS pitches, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN SKUs IS NULL THEN 'Unknown' WHEN SKUs < 5 THEN '<5' WHEN SKUs BETWEEN 5 AND 20 THEN '5-20' ELSE '20+' END;
        """,
        "explainer": "Checks whether very broad SKU assortments correlate with lower funded rates.",
        "explorer_prefill": {}
    },

    {
        "id": "myth13",
        "title": "Bootstrapped startups are funded more often",
        "context": "Compare funded rates for bootstrapped = 1 vs 0.",
        "check_sql": """
            SELECT
              SUM(CASE WHEN bootstrapped=TRUE THEN 1 ELSE 0 END) AS total_boot,
              SUM(CASE WHEN bootstrapped=TRUE AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_boot,
              SUM(CASE WHEN bootstrapped=FALSE THEN 1 ELSE 0 END) AS total_nonboot,
              SUM(CASE WHEN bootstrapped=FALSE AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_nonboot,
              CAST(SUM(CASE WHEN bootstrapped=TRUE AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN bootstrapped=TRUE THEN 1 ELSE 0 END),0) AS funded_rate_boot,
              CAST(SUM(CASE WHEN bootstrapped=FALSE AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN bootstrapped=FALSE THEN 1 ELSE 0 END),0) AS funded_rate_nonboot
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT COALESCE(CAST(bootstrapped AS VARCHAR(10)),'Unknown') AS bootstrapped, COUNT(*) AS cnt, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY COALESCE(CAST(bootstrapped AS VARCHAR(10)),'Unknown');
        """,
        "explainer": "Checks whether self-funded (bootstrapped) startups close at higher rates on the show.",
        "explorer_prefill": {}
    },

        {
        "id": "myth14",
        "title": "Deals with royalties close less often than equity-only deals",
        "context": "Compare closure rate for royalty deals vs equity-only (we do not assume a 'total_debt' column).",
        "check_sql": """
            SELECT
              SUM(CASE WHEN COALESCE(royalty_percentage,0) > 0 THEN 1 ELSE 0 END) AS total_royalty,
              SUM(CASE WHEN COALESCE(royalty_percentage,0) > 0 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS closed_royalty,
              SUM(CASE WHEN COALESCE(royalty_percentage,0) = 0 THEN 1 ELSE 0 END) AS total_equity_only,
              SUM(CASE WHEN COALESCE(royalty_percentage,0) = 0 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS closed_equity_only,
              CAST(SUM(CASE WHEN COALESCE(royalty_percentage,0) > 0 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN COALESCE(royalty_percentage,0) > 0 THEN 1 ELSE 0 END),0) AS closure_rate_royalty,
              CAST(SUM(CASE WHEN COALESCE(royalty_percentage,0) = 0 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN COALESCE(royalty_percentage,0) = 0 THEN 1 ELSE 0 END),0) AS closure_rate_equity
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN COALESCE(royalty_percentage,0) > 0 THEN 'Royalty' ELSE 'Equity-only' END AS instrument,
                      COUNT(*) AS pitches, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS closed
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN COALESCE(royalty_percentage,0) > 0 THEN 'Royalty' ELSE 'Equity-only' END;
        """,
        "explainer": "Compares closure likelihood for royalty-including deals vs straight equity-only deals (no debt column used).",
        "explorer_prefill": {}
    },

    {
        "id": "myth15",
        "title": "At least one investor focuses >50% of their deals in a single sector",
        "context": "Check whether any investor has >50% share of their deals in a single sector.",
        "check_sql": """
            WITH inv_sector AS (
              SELECT di.investor, COALESCE(d.sector,'Unknown') AS sector, COUNT(*) AS cnt
              FROM public.deal_investors di
              JOIN public.deals d ON di.staging_id = d.staging_id  -- Note: changed deal_id to staging_id for join
              GROUP BY di.investor, COALESCE(d.sector,'Unknown')
            ), inv_tot AS (
              SELECT investor, SUM(cnt) AS total FROM inv_sector GROUP BY investor
            ), inv_share AS (
              SELECT i.investor, i.sector, i.cnt, it.total, CAST(i.cnt AS FLOAT)/NULLIF(it.total,0) AS share
              FROM inv_sector i JOIN inv_tot it ON i.investor = it.investor
            )
            SELECT COUNT(*) AS investors_with_concentration
            FROM (
              SELECT investor, MAX(share) AS max_share
              FROM inv_share
              GROUP BY investor
            ) t
            WHERE max_share > 0.50;
        """,
        "plot_sql": """
            -- Note: vw_co_invest_pairs is not defined in the provided schema. Using a placeholder query.
            SELECT di.investor, COUNT(d.sector) AS deals_count, COALESCE(d.sector, 'Unknown') AS sector_name
            FROM public.deal_investors di
            JOIN public.deals d ON di.staging_id = d.staging_id
            GROUP BY 1, 3
            ORDER BY deals_count DESC
            LIMIT 50;
        """,
        "explainer": "Finds whether any shark has a sector concentration exceeding 50% of their deals.",
        "explorer_prefill": {}
    },

    {
        "id": "myth16",
        "title": "The investor who invests the most total also has the highest average ticket",
        "context": "Compare the top investor by total invested vs the top by average ticket.",
        "check_sql": """
            WITH invs AS (
              SELECT di.investor, SUM(COALESCE(di.invested_amount,0)) AS total_inv, AVG(NULLIF(di.invested_amount,0)) AS avg_ticket
              FROM public.deal_investors di
              -- The investor table already has the amount invested by that investor, using that instead of joining deals
              GROUP BY di.investor
            ), top_total AS (
              SELECT investor AS top_by_total FROM invs ORDER BY total_inv DESC LIMIT 1
            ), top_avg AS (
              SELECT investor AS top_by_avg FROM invs ORDER BY avg_ticket DESC LIMIT 1
            )
            SELECT (SELECT top_by_total FROM top_total) AS top_by_total, (SELECT top_by_avg FROM top_avg) AS top_by_avg;
        """,
        "plot_sql": """
            SELECT di.investor, SUM(COALESCE(di.invested_amount,0)) AS total_invested, AVG(NULLIF(di.invested_amount,0)) AS avg_ticket
            FROM public.deal_investors di
            GROUP BY di.investor
            ORDER BY total_invested DESC
            LIMIT 15;
        """,
        "explainer": "Verifies if the largest capital provider is also the one writing the largest average cheques.",
        "explorer_prefill": {}
    },

    {
        "id": "myth17",
        "title": "Deals with gross margin >=50% are funded at higher rates",
        "context": "Compare funded rates for gross_margin >= 50% vs <50%.",
        "check_sql": """
            SELECT
            SUM(CASE WHEN gross_margin >= 50 THEN 1 ELSE 0 END) AS total_high_margin,
            SUM(CASE WHEN gross_margin >= 50 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_high_margin,
            SUM(CASE WHEN gross_margin < 50 OR gross_margin IS NULL THEN 1 ELSE 0 END) AS total_low_margin,
            SUM(CASE WHEN (gross_margin < 50 OR gross_margin IS NULL) AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded_low_margin,
            CAST(SUM(CASE WHEN gross_margin >= 50 AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN gross_margin >= 50 THEN 1 ELSE 0 END),0) AS funded_rate_high_margin,
            CAST(SUM(CASE WHEN (gross_margin < 50 OR gross_margin IS NULL) AND invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS FLOAT)/NULLIF(SUM(CASE WHEN (gross_margin < 50 OR gross_margin IS NULL) THEN 1 ELSE 0 END),0) AS funded_rate_low_margin
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN gross_margin IS NULL THEN 'Unknown' WHEN gross_margin >= 50 THEN 'High margin' ELSE 'Low margin' END AS margin_bucket,
                    COUNT(*) AS pitches, SUM(CASE WHEN invested_amount IS NOT NULL THEN 1 ELSE 0 END) AS funded
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN gross_margin IS NULL THEN 'Unknown' WHEN gross_margin >= 50 THEN 'High margin' ELSE 'Low margin' END;
        """,
        "explainer": "Checks if better unit economics (high gross margins) correlate with better funded rates.",
        "explorer_prefill": {}
    },

    {
        "id": "myth18",
        "title": "Top-5 sectors by invested capital account for >50% of total invested capital",
        "context": "Compute share of total invested capital represented by the top 5 sectors (values in lakhs).",
        "check_sql": """
            WITH sector_sums AS (
              SELECT COALESCE(sector,'Unknown') AS sector, SUM(COALESCE(invested_amount,0)) AS total_invested
              FROM public.deals
              WHERE (%s = 'All' OR season = %s)
              GROUP BY COALESCE(sector,'Unknown')
            ), ranked AS (
              SELECT sector, total_invested, ROW_NUMBER() OVER (ORDER BY total_invested DESC) AS rn FROM sector_sums
            ), totals AS (
              SELECT SUM(total_invested) AS grand_total FROM sector_sums
            )
            SELECT
              (SELECT SUM(total_invested) FROM ranked WHERE rn <= 5) AS top5_total,
              (SELECT grand_total FROM totals) AS grand_total,
              CAST((SELECT SUM(total_invested) FROM ranked WHERE rn <= 5) AS FLOAT)/NULLIF((SELECT grand_total FROM totals),0) AS top5_share
            ;
        """,
        "plot_sql": """
            SELECT COALESCE(sector,'Unknown') AS sector, SUM(COALESCE(invested_amount,0)) AS total_invested
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY COALESCE(sector,'Unknown')
            ORDER BY total_invested DESC
            LIMIT 10;
        """,
        "explainer": "Measures capital concentration across sectors (top 5 vs total; values in lakhs).",
        "explorer_prefill": {}
    },

    {
        "id": "myth19",
        "title": "Average ticket size increased in the latest season vs the first season",
        "context": "Compare average invested_amount in the first season vs the last season present in the data.",
        "check_sql": """
            WITH season_avg AS (
              SELECT COALESCE(season,'Unknown') AS season, AVG(NULLIF(invested_amount,0)) AS avg_ticket
              FROM public.deals
              GROUP BY COALESCE(season,'Unknown')
            )
            SELECT MIN(season) AS first_season, MAX(season) AS last_season,
                      (SELECT avg_ticket FROM season_avg WHERE season = (SELECT MIN(season) FROM season_avg)) AS avg_first,
                      (SELECT avg_ticket FROM season_avg WHERE season = (SELECT MAX(season) FROM season_avg)) AS avg_last
            FROM season_avg;
        """,
        "plot_sql": """
            SELECT COALESCE(season,'Unknown') AS season, AVG(NULLIF(invested_amount,0)) AS avg_ticket
            FROM public.deals
            GROUP BY COALESCE(season,'Unknown')
            ORDER BY season;
        """,
        "explainer": "Compares earliest season average ticket vs latest season average ticket (values in lakhs).",
        "explorer_prefill": {}
    },

    {
        "id": "myth20",
        "title": "Deals that include advisory shares attract higher average investment",
        "context": "Compare avg invested_amount where advisory_shares_equity > 0 vs = 0 (values in lakhs).",
        "check_sql": """
            SELECT
              AVG(CASE WHEN COALESCE(advisory_shares_equity,0) > 0 THEN COALESCE(invested_amount,0) END) AS avg_with_advisory,
              AVG(CASE WHEN COALESCE(advisory_shares_equity,0) = 0 THEN COALESCE(invested_amount,0) END) AS avg_without_advisory
            FROM public.deals
            WHERE (%s = 'All' OR season = %s);
        """,
        "plot_sql": """
            SELECT CASE WHEN COALESCE(advisory_shares_equity,0) > 0 THEN 'Has advisory' ELSE 'No advisory' END AS advisory_flag,
                      COUNT(*) AS pitches, AVG(COALESCE(invested_amount,0)) AS avg_invested
            FROM public.deals
            WHERE (%s = 'All' OR season = %s)
            GROUP BY CASE WHEN COALESCE(advisory_shares_equity,0) > 0 THEN 'Has advisory' ELSE 'No advisory' END;
        """,
        "explainer": "Checks whether offering advisory equity is associated with larger investments (amounts in lakhs).",
        "explorer_prefill": {}
    }
]


# ----------------------
# Helper utilities
# ----------------------
def _safe_num(v, default=0.0):
    try:
        if v is None:
            return float(default)
        return float(v)
    except Exception:
        return float(default)

def _pct_str(frac):
    try:
        if frac is None:
            return "0.0%"
        return f"{float(frac)*100:.1f}%"
    except Exception:
        return "0.0%"

def evaluate_myth(myth_id, df_check):
    """
    Deterministic evaluation for each myth id.
    Always returns a tuple: (verdict_str, short_explanation_str)
    Verdict_str is either "True" or "False" (never Mixed).
    """
    # default fallback values
    if df_check is None or df_check.empty:
        # If no data, default to False and explain no data found.
        return "False", "Insufficient data in the selected season — defaulting verdict to False."

    r = df_check.iloc[0]

    # myth-specific logic (all return True/False deterministically)
    try:
        if myth_id == "myth01":
            closure_rate = _safe_num(r.get("closure_rate", 0.0))
            closed = int(_safe_num(r.get("closed_deals", 0)))
            total = int(_safe_num(r.get("total_onair", 0)))
            verdict = "True" if closure_rate > 0.5 else "False"
            expl = f"Closure rate = {_pct_str(closure_rate)} ({closed}/{total} pitches). Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth02":
            share = _safe_num(r.get("equity_only_share_among_funded", 0.0))
            total_funded = int(_safe_num(r.get("total_funded", 0)))
            equity_only = int(_safe_num(r.get("equity_only_funded", 0)))
            verdict = "True" if share > 0.5 else "False"
            expl = f"Equity-only funded deals = {equity_only}/{total_funded} ({_pct_str(share)}). Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth03":
            pct = _safe_num(r.get("pct_under_1cr", 0.0))
            total = int(_safe_num(r.get("total_funded", 0)))
            under = int(_safe_num(r.get("funded_under_1cr", 0)))
            verdict = "True" if pct > 0.5 else "False"
            expl = f"{under}/{total} funded deals are <1 Cr ({_pct_str(pct)}). Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth04":
            metro_rate = _safe_num(r.get("funded_rate_metro", 0.0))
            nonmetro_rate = _safe_num(r.get("funded_rate_nonmetro", 0.0))
            verdict = "True" if metro_rate > nonmetro_rate else "False"
            expl = f"Metro funded rate {_pct_str(metro_rate)} vs Non-metro {_pct_str(nonmetro_rate)}. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth05":
            fr = _safe_num(r.get("funded_rate_female_only", 0.0))
            mr = _safe_num(r.get("funded_rate_male_only", 0.0))
            vf = "True" if fr < mr else "False"
            expl = f"Female-only funded rate {_pct_str(fr)} vs Male-only {_pct_str(mr)}. Verdict: {vf}."
            return vf, expl

        if myth_id == "myth06":
                avg_multi = _safe_num(r.get("avg_multi", 0.0))
                avg_single = _safe_num(r.get("avg_single", 0.0))
                total_multi = int(_safe_num(r.get("total_multi", 0)))
                total_single = int(_safe_num(r.get("total_single", 0)))
                verdict = "True" if avg_multi > avg_single else "False"
                expl = f"Avg invested (multi-shark) = {avg_multi:.1f}L across {total_multi} deals vs single-shark = {avg_single:.1f}L across {total_single} deals. Verdict: {verdict}."
                return verdict, expl

        if myth_id == "myth07":
            pct = _safe_num(r.get("pct_multi_shark", 0.0))
            total = int(_safe_num(r.get("total_funded", 0)))
            multi = int(_safe_num(r.get("multi_shark_funded", 0)))
            verdict = "True" if pct > 0.5 else "False"
            expl = f"{multi}/{total} funded deals involved multiple sharks ({_pct_str(pct)}). Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth08":
            avg_asked = _safe_num(r.get("avg_asked_equity", 0.0))
            avg_final = _safe_num(r.get("avg_final_equity", 0.0))
            verdict = "True" if avg_final > avg_asked else "False"
            expl = f"Avg asked equity {avg_asked:.2f}% vs avg final equity {avg_final:.2f}%. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth09":
            avg_ask_val = _safe_num(r.get("avg_ask_valuation", 0.0))
            avg_deal_val = _safe_num(r.get("avg_deal_valuation", 0.0))
            verdict = "True" if avg_deal_val < avg_ask_val else "False"
            expl = f"Avg ask valuation {avg_ask_val:.0f}L vs avg deal valuation {avg_deal_val:.0f}L. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth10":
            mf = _safe_num(r.get("avg_monthly_funded", 0.0))
            mnf = _safe_num(r.get("avg_monthly_notfunded", 0.0))
            verdict = "True" if mf > mnf else "False"
            expl = f"Avg monthly sales (funded) = {int(mf):,} vs not-funded = {int(mnf):,}. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth11":
            rp = _safe_num(r.get("funded_rate_patent", 0.0))
            rnp = _safe_num(r.get("funded_rate_no_patent", 0.0))
            verdict = "True" if rp > rnp else "False"
            expl = f"Patent-funded rate {_pct_str(rp)} vs no-patent {_pct_str(rnp)}. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth12":
            rh = _safe_num(r.get("funded_rate_high_skus", 0.0))
            rl = _safe_num(r.get("funded_rate_low_skus", 0.0))
            verdict = "True" if rh < rl else "False"
            expl = f"Funded rate (SKUs>20) {_pct_str(rh)} vs SKUs<=20 {_pct_str(rl)}. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth13":
            rb = _safe_num(r.get("funded_rate_boot", 0.0))
            rnb = _safe_num(r.get("funded_rate_nonboot", 0.0))
            verdict = "True" if rb > rnb else "False"
            expl = f"Bootstrapped funded rate {_pct_str(rb)} vs non-boot {_pct_str(rnb)}. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth14":
            cr_roy = _safe_num(r.get("closure_rate_royalty", 0.0))
            cr_eq = _safe_num(r.get("closure_rate_equity", 0.0))
            verdict = "True" if cr_roy < cr_eq else "False"
            expl = f"Royalty closure {_pct_str(cr_roy)} vs equity-only {_pct_str(cr_eq)}. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth15":
            cnt = int(_safe_num(r.get("investors_with_concentration", 0)))
            verdict = "True" if cnt > 0 else "False"
            expl = f"Investors with >50% sector concentration: {cnt}. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth16":
            a = (r.get("top_by_total") or "").strip()
            b = (r.get("top_by_avg") or "").strip()
            verdict = "True" if a != "" and a == b else "False"
            expl = f"Top by total: '{a}' vs top by avg: '{b}'. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth17":
            rh = _safe_num(r.get("funded_rate_high_margin", 0.0))
            rl = _safe_num(r.get("funded_rate_low_margin", 0.0))
            verdict = "True" if rh > rl else "False"
            expl = f"Funded rate (gross margin >=50%) {_pct_str(rh)} vs (<50%) {_pct_str(rl)}. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth18":
            share = _safe_num(r.get("top5_share", 0.0))
            top5 = _safe_num(r.get("top5_total", 0.0))
            grand = _safe_num(r.get("grand_total", 0.0))
            verdict = "True" if share > 0.5 else "False"
            expl = f"Top5 invested = {top5:.0f}L of {grand:.0f}L ({_pct_str(share)}). Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth19":
            first = _safe_num(r.get("avg_first", 0.0))
            last = _safe_num(r.get("avg_last", 0.0))
            verdict = "True" if last > first else "False"
            expl = f"Avg first season {first:.1f}L vs last season {last:.1f}L. Verdict: {verdict}."
            return verdict, expl

        if myth_id == "myth20":
            wa = _safe_num(r.get("avg_with_advisory", 0.0))
            wo = _safe_num(r.get("avg_without_advisory", 0.0))
            verdict = "True" if wa > wo else "False"
            expl = f"Avg invested with advisory {wa:.1f}L vs without {wo:.1f}L. Verdict: {verdict}."
            return verdict, expl

    except Exception as ex:
        # safety fallback: always return False (deterministic) with error note
        return "False", f"Evaluation failed safely: {str(ex)} (default False)."

    # default
    return "False", "Could not evaluate (default False)."


# ----------------------
# Page main
# ----------------------
def page_myths(filters):
    st.title("Myth Buster")
    season = filters.get("season", "All")
    view_sql = filters.get("view_sql", False)

    st.markdown("Select a myth below. Each myth is tested deterministically using the dataset.")

    # Build choices
    titles = [m['title'] for m in MYTHS]
    selected_title = st.selectbox("Select a myth", titles)

    myth = next((m for m in MYTHS if m['title'] == selected_title), None)
    if myth is None:
        st.error("Selected myth not found.")
        return

    # Run check SQL
    df_check = None
    try:
        # FIX: Pass parameters as a tuple for positional placeholders
        params_tuple = (season, season)
        
        # NOTE: Using 'public.deals' instead of 'dbo.deals' for Postgres schema compatibility
        check_sql_fixed = myth['check_sql'].replace('dbo.deals', 'public.deals').replace(':season', '%s')
        
        df_check = cached_query(check_sql_fixed, params_tuple)
    except Exception as e:
        st.error("Could not run check SQL: " + str(e))
        return

    verdict, verdict_expl = evaluate_myth(myth['id'], df_check)

    # Quick metric summary (pick numeric fields to surface)
    quick_metric = ""
    if df_check is not None and not df_check.empty:
        r = df_check.iloc[0]
        # prefer known fields
        for pref in ["closure_rate", "equity_only_share_among_funded", "pct_under_1cr",
                     "funded_rate_metro", "funded_rate_nonmetro",
                     "funded_rate_female_only", "funded_rate_male_only"]:
            if pref in r.index:
                val = r.get(pref)
                if pd.api.types.is_number(val):
                    quick_metric = f"{pref}: {_pct_str(_safe_num(val))}"
                    break
        if quick_metric == "":
            # fallback: list first numeric column
            for c in r.index:
                if pd.api.types.is_numeric_dtype(r[c]):
                    quick_metric = f"{c}: {r[c]}"
                    break
    else:
        quick_metric = "No data available"

    # Layout: left (myth), middle (evidence), right (sql + actions)
    cols = st.columns([3, 5])

    with cols[0]:
        st.subheader(myth['title'])
        st.write(myth['context'])
        st.markdown(f"**Quick metric:** {quick_metric}")
        color = "#16a34a" if verdict == "True" else "#ef4444"
        st.markdown(f"<div style='padding:6px;border-radius:6px;background:{color};color:white;display:inline-block;font-weight:700'>{verdict}</div>", unsafe_allow_html=True)
        st.markdown("**Why this matters:**")
        st.write(myth['explainer'])
        st.subheader("Conclusion")
        st.write(verdict_expl)
        # Add 2-3 line business interpretation
        if verdict == "True":
            st.write("Interpretation: dataset supports the myth under the deterministic rule we used. Use this as an actionable signal, not absolute proof — consider sampling and domain knowledge.")
        else:
            st.write("Interpretation: dataset does not support the myth under our deterministic rule. This suggests the myth is likely false for this dataset; consider edge cases or season-specific behavior.")

    with cols[1]:
        # st.markdown("### Evidence")
        st.markdown("<h3 style='text-align: center;'>Evidence</h3>", unsafe_allow_html=True)
        try:
            # FIX: Changed parameter passing from dict to a tuple/list for positional %s
            # df_plot = cached_query(myth['plot_sql'], (season,))
            df_plot = cached_query(myth['plot_sql'], (season, season))
            if df_plot is not None and not df_plot.empty:
                # If plot has 'funded' and 'pitches', show funded rate bar
                if 'funded' in df_plot.columns and 'pitches' in df_plot.columns:
                    df_plot = df_plot.copy()
                    df_plot['funded_rate'] = df_plot['funded'] / df_plot['pitches'].replace({0: None})
                    x_col = df_plot.columns[0]
                    fig = px.bar(df_plot, x=x_col, y='funded_rate', title="Funded rate by bucket", labels={'funded_rate':'Funded rate', x_col:x_col})
                    st.plotly_chart(fig, use_container_width=True)
                    st.dataframe(df_plot)
                else:
                    # fallback: plot first numeric column
                    numeric_cols = [c for c in df_plot.columns if pd.api.types.is_numeric_dtype(df_plot[c])]
                    if numeric_cols:
                        fig = px.bar(df_plot, x=df_plot.columns[0], y=numeric_cols[0], title=f"{numeric_cols[0]} by {df_plot.columns[0]}")
                        st.plotly_chart(fig, use_container_width=True)
                        st.dataframe(df_plot)
                    else:
                        st.dataframe(df_plot)
            else:
                st.info("No evidence data available for this myth (dataset may be missing required fields).")
        except Exception as e:
            st.warning("Evidence SQL failed: " + str(e))