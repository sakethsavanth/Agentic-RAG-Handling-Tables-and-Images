-- Generated Tables from: Business Ready 2025
-- Generated at: 2026-01-07 13:41:50
-- Total tables: 6
-- ======================================================================

-- Table: mature_workforce_table_1
-- Source: Business Ready 2025, table_1
CREATE TABLE IF NOT EXISTS mature_workforce_table_1 (
    col1 TEXT,
    col2 TEXT,
    col3 TEXT,
    col4 TEXT
);

INSERT INTO mature_workforce_table_1 (col1, col2, col3, col4) VALUES 
('NA', 'NA', 'NA', 'NA'),
('NA', 'NA', 'NA', 'NA'),
('NA', 'NA', 'NA', 'NA'),
('NA', 'NA', 'NA', 'NA');


-- Table: workforce_challenges_matrix_table_2
-- Source: Business Ready 2025, table_2
CREATE TABLE IF NOT EXISTS workforce_challenges_matrix_table_2 (
    id SERIAL PRIMARY KEY,
    need_to_boost_productivity_and_innovation TEXT,
    col2 TEXT,
    need_to_maintain_productivity_and_technology_adoption TEXT
);

INSERT INTO workforce_challenges_matrix_table_2 (need_to_boost_productivity_and_innovation, col2, need_to_maintain_productivity_and_technology_adoption) VALUES
('NA', 'Enable resource and job reallocation to more productive sectors', 'NA'),
('Overhaul business climate to facilitate more and better jobs', 'NA', 'Channel growth into more and better jobs');


-- Table: regulatory_framework_pillar_table_3
-- Source: Business Ready 2025, table_3
CREATE TABLE IF NOT EXISTS regulatory_framework_pillar_table_3 (
    col1 TEXT,
    col2 TEXT,
    col3 TEXT,
    col4 TEXT,
    col5 TEXT,
    col6 TEXT
);

INSERT INTO regulatory_framework_pillar_table_3 (col1, col2, col3, col4, col5, col6) VALUES
('NA', '12 66', '12 66', '12 66', '12 66', '12 66'),
('NA', '12 66', 'NA', 'NA', 'NA', 'NA'),
('NA', 'NA', 'NA', '-54', '-54', '-54'),
('NA', 'NA', 'NA', '-54', 'NA', 'NA'),
('NA', 'NA', 'NA', 'NA', 'NA', 'NA'),
('NA', 'NA', 'NA', 'NA', 'NA', 'NA');


-- Table: pillar_performance_data_table_4
-- Source: Business Ready 2025, table_4
CREATE TABLE IF NOT EXISTS pillar_performance_data_table_4 (
    pillar_i_country TEXT,
    pillar_i_score NUMERIC,
    pillar_ii_country TEXT,
    pillar_ii_score NUMERIC,
    pillar_iii_country TEXT,
    pillar_iii_score NUMERIC
);

INSERT INTO pillar_performance_data_table_4 (pillar_i_country, pillar_i_score, pillar_ii_country, pillar_ii_score, pillar_iii_country, pillar_iii_score) VALUES
('Slovenia', 75.03, 'Hungary', 68.42, 'Belgium', 68.16),
('Colombia', 74.98, 'Poland', 68.34, 'United States', 68.02),
('Hungary', 74.71, 'Taiwan, China', 68.03, 'Malaysia', 67.99),
('Belgium', 74.08, 'Costa Rica', 67.06, 'Iceland', 67.97),
('Philippines', 73.86, 'Sweden', 67.06, 'Croatia', 67.82),
('North Macedonia', 73.62, 'Greece', 66.91, 'Moldova', 67.46),
('Israel', 73.03, 'Bahrain', 66.89, 'Slovenia', 67.32),
('Armenia', 72.91, 'Bulgaria', 66.51, 'Bulgaria', 66.52),
('Costa Rica', 72.69, 'Ireland', 66.43, 'Kazakhstan', 66.40),
('Rwanda', 72.54, 'Romania', 66.12, 'Romania', 66.34),
('Azerbaijan', 71.92, 'Armenia', 66.05, 'Bhutan', 66.29),
('Canada', 71.80, 'Hong Kong SAR, China', 65.32, 'Barbados', 65.64),
('Hong Kong SAR, China', 71.03, 'Uzbekistan', 65.12, 'Mauritius', 65.44),
('Sweden', 70.54, 'Morocco', 64.55, 'Tajikistan', 64.62),
('Cyprus', 70.43, 'Mexico', 64.18, 'Spain', 64.55),
('Morocco', 70.06, 'Moldova', 64.05, 'Malta', 64.35),
('Mexico', 69.54, 'Malaysia', 63.41, 'Montenegro', 64.16),
('Uzbekistan', 69.52, 'Peru', 63.24, 'Italy', 64.10),
('Kazakhstan', 69.51, 'Azerbaijan', 62.68, 'Poland', 63.63),
('Taiwan, China', 69.38, 'Indonesia', 62.00, 'Kyrgyz Republic', 63.56),
('New Zealand', 69.22, 'Serbia', 61.53, 'Azerbaijan', 63.34),
('Ghana', 68.88, 'Togo', 60.92, 'Bosnia and Herzegovina', 62.93),
('Benin', 68.55, 'Cyprus', 60.53, 'Türkiye', 62.91),
('Côte d’Ivoire', 68.46, 'Rwanda', 59.81, 'Greece', 61.64),
('Peru', 68.25, 'North Macedonia', 59.75, 'Armenia', 61.18),
('Jordan', 67.90, 'Mauritius', 59.48, 'Eswatini', 60.79),
('Bahrain', 67.50, 'Jordan', 57.97, 'Jamaica', 60.52),
('Senegal', 67.42, 'Benin', 57.87, 'Botswana', 60.37),
('Iceland', 67.35, 'Tanzania', 57.87, 'Lao PDR', 60.06),
('Uruguay', 67.32, 'Philippines', 57.82, 'Turkmenistan', 59.88),
('Ecuador', 67.22, 'Jamaica', 57.07, 'Portugal', 59.74),
('Malta', 67.22, 'Paraguay', 56.11, 'Pakistan', 59.64),
('Kyrgyz Republic', 67.20, 'Ecuador', 56.02, 'Israel', 59.18),
('Viet Nam', 67.03, 'Iceland', 55.84, 'Jordan', 59.17);


-- Table: appendix_a_pillar_scores_table_5
-- Source: Business Ready 2025, table_5
CREATE TABLE IF NOT EXISTS appendix_a_pillar_scores_table_5 (
    pillar_i_country TEXT,
    pillar_i_score NUMERIC,
    pillar_ii_country TEXT,
    pillar_ii_score NUMERIC,
    pillar_iii_country TEXT,
    pillar_iii_score NUMERIC
);

INSERT INTO appendix_a_pillar_scores_table_5 (pillar_i_country, pillar_i_score, pillar_ii_country, pillar_ii_score, pillar_iii_country, pillar_iii_score) VALUES
('Türkiye', 66.81, 'Malta', 55.59, 'Colombia', 59.06),
('Togo', 66.26, 'Pakistan', 54.58, 'Indonesia', 59.01),
('Mali', 65.99, 'Viet Nam', 53.93, 'Samoa', 58.31),
('Indonesia', 65.61, 'Kyrgyz Republic', 51.88, 'Bangladesh', 57.77),
('Malaysia', 65.61, 'Montenegro', 51.85, 'Togo', 57.38),
('Mauritius', 64.69, 'Ghana', 49.99, 'Seychelles', 57.35),
('Fourth quintile', NULL, 'Fourth quintile', NULL, 'Fourth quintile', NULL),
('Botswana', 64.38, 'El Salvador', 49.40, 'Senegal', 56.74),
('Namibia', 64.21, 'Uruguay', 48.68, 'Cameroon', 56.63),
('Jamaica', 64.07, 'Barbados', 48.39, 'Cabo Verde', 56.55),
('Angola', 63.88, 'Côte d’Ivoire', 46.94, 'Cyprus', 56.44),
('Cabo Verde', 63.71, 'Botswana', 45.37, 'Cambodia', 56.17),
('Congo, Dem. Rep.', 63.61, 'Bosnia and Herzegovina', 45.25, 'Nepal', 56.15),
('Burkina Faso', 63.23, 'Bangladesh', 45.14, 'Morocco', 55.71),
('Paraguay', 63.12, 'Trinidad and Tobago', 44.83, 'Uruguay', 55.57),
('Cambodia', 63.06, 'Namibia', 44.57, 'Tanzania', 55.25),
('Tunisia', 62.56, 'Senegal', 44.00, 'Costa Rica', 55.15),
('Bosnia and Herzegovina', 62.55, 'Cambodia', 43.14, 'Ecuador', 55.11),
('Pakistan', 62.31, 'Tunisia', 43.02, 'Peru', 54.85),
('Tanzania', 61.92, 'Nepal', 42.04, 'Tonga', 54.25),
('Barbados', 61.67, 'Bhutan', 41.87, 'Benin', 54.22),
('Nepal', 61.46, 'Eswatini', 41.12, 'Lesotho', 54.19),
('Trinidad and Tobago', 61.16, 'Burkina Faso', 40.86, 'Tunisia', 52.46),
('Madagascar', 60.37, 'Tajikistan', 40.35, 'Mexico', 52.45),
('Tajikistan', 59.81, 'Lesotho', 39.27, 'Ghana', 51.73),
('Eswatini', 59.70, 'Seychelles', 39.09, 'Philippines', 51.45),
('El Salvador', 59.08, 'Angola', 37.48, 'Vanuatu', 51.40),
('Fifth quintile', NULL, 'Fifth quintile', NULL, 'Fifth quintile', NULL),
('Cameroon', 58.75, 'Cameroon', 36.30, 'West Bank and Gaza', 51.36),
('Seychelles', 58.73, 'Lao PDR', 35.62, 'Paraguay', 51.32),
('Sierra Leone', 56.96, 'Mali', 35.40, 'El Salvador', 50.37),
('Samoa', 56.77, 'West Bank and Gaza', 35.03, 'Burkina Faso', 49.98),
('Vanuatu', 55.85, 'Cabo Verde', 34.54, 'Madagascar', 49.95),
('Lesotho', 55.58, 'Samoa', 34.23, 'Trinidad and Tobago', 49.68),
('Papua New Guinea', 55.28, 'Vanuatu', 33.64, 'Namibia', 48.90),
('Gambia, The', 53.97, 'Papua New Guinea', 33.46, 'Côte d’Ivoire', 47.90);


-- Table: b_ready_2025_data_table_6
-- Source: Business Ready 2025, table_6
CREATE TABLE IF NOT EXISTS b_ready_2025_data_table_6 (
    economy_name TEXT,
    pillar_i_score NUMERIC,
    pillar_ii_score NUMERIC,
    pillar_iii_score NUMERIC
);

INSERT INTO b_ready_2025_data_table_6 (economy_name, pillar_i_score, pillar_ii_score, pillar_iii_score) VALUES
('Bangladesh', 53.01, 'NA', 'NA'),
('Madagascar', 'NA', 33.40, 'NA'),
('Mali', 'NA', 'NA', 47.51),
('Central African Republic', 52.78, 'NA', 'NA'),
('Tonga', 'NA', 32.34, 'NA'),
('Congo, Dem. Rep.', 'NA', 'NA', 46.97),
('Congo, Rep.', 52.21, 'NA', 'NA'),
('Sierra Leone', 'NA', 30.00, 'NA'),
('Angola', 'NA', 'NA', 45.85),
('Bhutan', 52.19, 'NA', 'NA'),
('Turkmenistan', 'NA', 28.60, 'NA'),
('Gambia, The', 'NA', 'NA', 45.79),
('Chad', 51.78, 'NA', 'NA'),
('Gambia, The', 'NA', 27.22, 'NA'),
('Sierra Leone', 'NA', 'NA', 45.61),
('Lao PDR', 50.88, 'NA', 'NA'),
('Congo, Dem. Rep.', 'NA', 26.56, 'NA'),
('South Sudan', 'NA', 'NA', 45.36),
('Turkmenistan', 50.46, 'NA', 'NA'),
('Congo, Rep.', 'NA', 24.90, 'NA'),
('Congo, Rep.', 'NA', 'NA', 45.03),
('West Bank and Gaza', 49.67, 'NA', 'NA'),
('Timor-Leste', 'NA', 24.20, 'NA'),
('Equatorial Guinea', 'NA', 'NA', 44.01),
('Tonga', 45.35, 'NA', 'NA'),
('Equatorial Guinea', 'NA', 23.40, 'NA'),
('Papua New Guinea', 'NA', 'NA', 42.69),
('Timor-Leste', 42.78, 'NA', 'NA'),
('Equatorial Guinea', 'NA', 16.84, 'NA'),
('Chad', 'NA', 'NA', 40.22),
('South Sudan', 36.04, 'NA', 'NA'),
('South Sudan', 'NA', 15.51, 'NA'),
('Central African Republic', 'NA', 'NA', 35.48);
