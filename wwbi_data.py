import os
import pandas as pd
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class WWBIDataService:
    _instance = None
    _data_cache = None

    @staticmethod
    def get_instance():
        if WWBIDataService._instance is None:
            WWBIDataService._instance = WWBIDataService()
        return WWBIDataService._instance

    def __init__(self):
        self.csv_path = os.path.join(os.path.dirname(__file__), 'WWBI_CSV', 'WWBICSV.csv')
        self._load_data()

    def _load_data(self):
        """Load and transform WWBI data once at initialization"""
        if WWBIDataService._data_cache is not None:
            return

        logging.info(f"Loading WWBI data from {self.csv_path}")

        df = pd.read_csv(self.csv_path)

        year_cols = [col for col in df.columns if col.isdigit()]
        id_cols = ['Country Name', 'Country Code', 'Indicator Name', 'Indicator Code']

        df_long = df.melt(
            id_vars=id_cols,
            value_vars=year_cols,
            var_name='year',
            value_name='value'
        )

        df_long['year'] = df_long['year'].astype(int)
        df_long = df_long.dropna(subset=['value'])

        df_long = df_long.rename(columns={
            'Country Name': 'country_name',
            'Country Code': 'country_code',
            'Indicator Name': 'indicator_name',
            'Indicator Code': 'indicator_code'
        })

        WWBIDataService._data_cache = df_long
        logging.info(f"WWBI data loaded: {len(df_long)} records")

    def get_indicators(self, indicator_codes, country_whitelist=None):
        """
        Get specific WWBI indicators.

        Args:
            indicator_codes: List of indicator codes (e.g., ['BI.EMP.PWRK.PB.ZS'])
            country_whitelist: Optional list of countries to filter by

        Returns:
            DataFrame with columns: country_name, year, indicator_code, indicator_name, value
        """
        df = WWBIDataService._data_cache.copy()

        df = df[df['indicator_code'].isin(indicator_codes)]

        if country_whitelist is not None:
            df = df[df['country_name'].isin(country_whitelist)]

        return df[['country_name', 'country_code', 'year', 'indicator_code', 'indicator_name', 'value']]

    def get_indicator_pivot(self, indicator_codes, country_whitelist=None):
        """
        Get indicators in pivot format with one column per indicator.

        Args:
            indicator_codes: List of indicator codes
            country_whitelist: Optional list of countries to filter by

        Returns:
            DataFrame with columns: country_name, year, [indicator_code columns]
        """
        df = self.get_indicators(indicator_codes, country_whitelist)

        pivot_df = df.pivot_table(
            index=['country_name', 'year'],
            columns='indicator_code',
            values='value',
            aggfunc='first'
        ).reset_index()

        print(pivot_df)
        return pivot_df

    def get_public_private_employment(self, country_whitelist=None):
        """Get public vs private sector employment data"""
        indicator_codes = [
            'BI.EMP.PWRK.PB.ZS',
            'BI.EMP.PWRK.PB.FE.ZS',  # Female public employment share
            'BI.EMP.PWRK.PB.MA.ZS',  # Male public employment share
        ]
        return self.get_indicator_pivot(indicator_codes, country_whitelist)

    def get_wage_premium_data(self, country_whitelist=None):
        """Get public sector wage premium indicators"""
        indicator_codes = [
            'BI.WAG.PREM.PB',  # Overall wage premium
            'BI.WAG.PREM.PB.FE',  # Female wage premium
            'BI.WAG.PREM.ED.GP',  # Education sector premium
            'BI.WAG.PREM.HE.GP',  # Health sector premium
            'BI.WAG.PREM.FE.ED',  # Female education premium
            'BI.WAG.PREM.FE.HE',  # Female health premium
            'BI.WAG.PREM.MA.ED',  # Male education premium
            'BI.WAG.PREM.MA.HE',  # Male health premium
        ]
        return self.get_indicator_pivot(indicator_codes, country_whitelist)

    def get_employment_composition(self, country_whitelist=None):
        """Get public sector employment composition by sector"""
        indicator_codes = [
            'BI.EMP.PWRK.ED.PB.ZS',  # Education workers as % of public employees
            'BI.EMP.PWRK.HE.PB.ZS',  # Health workers
            'BI.EMP.PWRK.CA.PB.ZS',  # Core admin workers
            'BI.EMP.PWRK.PS.PB.ZS',  # Public safety workers
            'BI.EMP.PWRK.SS.PB.ZS',  # Social security workers
            'BI.EMP.PWRK.PA.PB.ZS',  # Public administration workers
        ]
        return self.get_indicator_pivot(indicator_codes, country_whitelist)

    def get_gender_employment_data(self, country_whitelist=None):
        """Get gender disaggregated employment data"""
        indicator_codes = [
            'BI.EMP.PWRK.PB.FE.ZS',  # Overall female share
            'BI.EMP.PUBS.FE.ED.ZS',  # Female in education
            'BI.EMP.PUBS.FE.HE.ZS',  # Female in health
            'BI.EMP.PUBS.FE.SN.ZS',  # Female managers
            'BI.EMP.PUBS.FE.PN.ZS',  # Female professionals
            'BI.EMP.PUBS.FE.CK.ZS',  # Female clerks
            'BI.EMP.PWRK.PS.PB.ZS',  # Public safety (for comparison)
        ]
        return self.get_indicator_pivot(indicator_codes, country_whitelist)
