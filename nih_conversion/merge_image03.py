import csv
import os
import pandas as pd

import sys
sys.path.append('..')
import common

from datetime import datetime
from getpass import getuser, getpass
from gooey import Gooey, GooeyParser

study_dir = r'\\neuroimage\nil\black\NewTics'
box_dir = r'C:\Users\{}\Box\Black_Lab\projects\TS\New Tics R01\Data\NIH Data Archive\conversion\import_forms'.format(getuser())

"""
Create final image03 submission file
    Add in demographic info needed for submission that we couldn't access on Unix (because it lives on Box)
"""
def merge_image03(r01_file=None, api_db_password=None, to_date=None):
    # read in file generated by gen_image03 
    image03_csv = os.path.join(study_dir, 'image03_nodemo.csv')
    image_df = pd.read_csv(image03_csv)

    # extract DOB from REDCap project (doesn't appear in any submission forms)
    dob_df = common.get_project_df('r01', r01_file, api_db_password, ['demo_dob']).reset_index()
    dob_df = dob_df[dob_df['redcap_event_name'] == 'screening_visit_arm_1']

    # merge DOB df into image df and calculate age in months for each scan
    image_df = image_df.merge(dob_df, on='demo_study_id')
    image_df['interview_date'] = pd.to_datetime(image_df['interview_date'], format='%Y%m%d')
    image_df['interview_age'] = (image_df['interview_date'] - pd.to_datetime(image_df['demo_dob'])).apply(lambda x: round(.0328767*x.days) if pd.notnull(x) else np.nan)
    image_df['interview_date'] = image_df['interview_date'].map(lambda x: x.strftime('%m/%d/%Y') if pd.notnull(x) else x) # convert to NIH date format
    image_df = image_df.drop(columns=['demo_dob', 'redcap_event_name']) # remove columns that aren't part of submission (i.e. for calculation only)
    image_df['image_file'] = image_df['image_file'].apply(lambda x: os.path.join(study_dir, os.path.basename(x))) # change filepath to match Windows path (since originally created on unix)

    # filter out scans before date 
    #   (we only submit new imaging data each time)
    if to_date:
        image_df = image_df[pd.to_datetime(image_df['interview_date']) < to_date]

    # extract GUID (aka subjectkey) and sex from one of the other submission forms and merge into final df
    socdemo_df = pd.read_csv(os.path.join(box_dir, 'socdem01.csv'), skiprows=1) # skiprows to skip first line (NIH header)
    socdemo_df = socdemo_df[['demo_study_id', 'gender', 'subjectkey']] 
    image_df = image_df.merge(socdemo_df, on='demo_study_id')

    # write NIH header into file
    outfile = os.path.join(box_dir, 'image03.csv')
    with open(outfile, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['image', '3'])

    image_df.to_csv(outfile, mode='a', index=False, float_format='%g') # save form data to file



if __name__ == '__main__':
    @Gooey
    def parse_args():
        parser = GooeyParser()
        parser.add_argument('--r01_file', widget='FileChooser', help='file containing data exported from R01 redcap project')
        parser.add_argument('--api_db_password', widget='PasswordField', help='password for access db with REDCap API tokens (only needed if not supplying data files)')
        parser.add_argument('--to_date', widget='DateChooser', type=lambda d: datetime.strptime(d, '%Y-%m-%d'), help='only process subjects up until date')
        return parser.parse_args()

    args = parse_args()
    merge_image03(args.r01_file, args.api_db_password, args.to_date)
