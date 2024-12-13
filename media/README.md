# Dataset Summary Insights

## General Information
- **Total Rows:** 2652
- **Total Columns:** 8

## Columns Overview
| Column Name     | Data Type | Non-Null Count |
|------------------|-----------|-----------------|
| date             | object    | 2553            |
| language         | object    | 2652            |
| type             | object    | 2652            |
| title            | object    | 2652            |
| by               | object    | 2390            |
| overall          | int64     | 2652            |
| quality          | int64     | 2652            |
| repeatability    | int64     | 2652            |

### Key Observations
- **Missing Data:**
  - The `date` column has 99 missing entries (non-null count: 2553).
  - The `by` column has 262 missing entries (non-null count: 2390).

- **Complete Data:**
  - All entries in `language`, `type`, `title`, `overall`, `quality`, and `repeatability` columns have complete data.

## Correlation Insights
A correlation heatmap shows the following relationships among the numerical columns:

|                   | overall | quality | repeatability |
|-------------------|---------|---------|---------------|
| overall           | 1.00    | 0.83    | 0.51          |
| quality           | 0.83    | 1.00    | 0.31          |
| repeatability     | 0.51    | 0.31    | 1.00          |

### Key Correlation Findings
- **Overall and Quality:** Strong positive correlation (0.83) indicating that higher overall ratings are associated with higher quality ratings.
- **Overall and Repeatability:** Moderate positive correlation (0.51) suggests some association between overall ratings and the repeatability of the entries.
- **Quality and Repeatability:** Weaker correlation (0.31) implying lesser association between quality ratings and repeatability.

## Conclusion
The dataset comprises a rich collection of entries with detailed metrics on overall performance, quality, and repeatability. While the relationship between overall and quality is particularly strong, there are actionable insights to consider in enhancing repeatability.