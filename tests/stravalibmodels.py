#!/usr/bin/env python3
"""
Test script to explore stravalib models and data availability.
This script helps debug what data is available from the Strava API,
particularly for heart rate data and other activity details.

Usage:
    # Show model definitions without fetching activities
    python tests/stravalibmodels.py --show-models
    
    # Analyze recent activities
    python tests/stravalibmodels.py --athlete-id YOUR_STRAVA_ID
    
    # Analyze with detailed data and streams
    python tests/stravalibmodels.py --athlete-id YOUR_STRAVA_ID --detailed --streams
    
    # Analyze a specific activity
    python tests/stravalibmodels.py --athlete-id YOUR_STRAVA_ID --activity-id ACTIVITY_ID
    
Options:
    --athlete-id    Your Strava athlete ID (get from database after logging in)
    --limit         Number of activities to fetch (default: 5)
    --detailed      Fetch detailed activity data including segment efforts
    --streams       Fetch activity streams (time-series heart rate, cadence, etc.)
    --verbose       Enable verbose logging and show model definitions
    --activity-id   Analyze a specific activity by ID
    --show-models   Show stravalib model definitions and exit (no API calls)

This script references the stravalib model files:
    venv/lib/python3.11/site-packages/stravalib/strava_model.py
    venv/lib/python3.11/site-packages/stravalib/model.py
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
from pprint import pprint

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from stravalib import Client
from dotenv import load_dotenv
from db import db_utils as db
import helpers as h

# Import stravalib models to inspect them
try:
    from stravalib import strava_model
    STRAVA_MODEL_AVAILABLE = True
except ImportError:
    try:
        from stravalib import model as strava_model
        STRAVA_MODEL_AVAILABLE = True
    except ImportError:
        STRAVA_MODEL_AVAILABLE = False

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def inspect_model_definitions():
    """Inspect the stravalib model definitions to show what fields are available"""
    if not STRAVA_MODEL_AVAILABLE:
        print("❌ Could not import stravalib models")
        return
    
    print_section("STRAVALIB MODEL DEFINITIONS")
    
    # Get the model classes
    summary_activity = getattr(strava_model, 'SummaryActivity', None)
    detailed_activity = getattr(strava_model, 'DetailedActivity', None)
    detailed_segment_effort = getattr(strava_model, 'DetailedSegmentEffort', None)
    lap = getattr(strava_model, 'Lap', None)
    
    if summary_activity:
        print("📋 SummaryActivity (from get_activities()):")
        print("   This is what you get when calling client.get_activities()\n")
        
        # Get model fields using Pydantic
        if hasattr(summary_activity, 'model_fields'):
            fields = summary_activity.model_fields
        elif hasattr(summary_activity, '__fields__'):
            fields = summary_activity.__fields__
        else:
            fields = {}
        
        # Look for heart rate and performance related fields
        hr_fields = [f for f in fields.keys() if 'heart' in f.lower()]
        power_fields = [f for f in fields.keys() if 'power' in f.lower() or 'watt' in f.lower()]
        cadence_fields = [f for f in fields.keys() if 'cadence' in f.lower()]
        speed_fields = [f for f in fields.keys() if 'speed' in f.lower()]
        
        print(f"   Total fields: {len(fields)}")
        print(f"   Heart rate fields: {hr_fields if hr_fields else 'NONE ⚠️'}")
        print(f"   Power fields: {power_fields if power_fields else 'None'}")
        print(f"   Cadence fields: {cadence_fields if cadence_fields else 'None'}")
        print(f"   Speed fields: {speed_fields if speed_fields else 'None'}")
        print()
    
    if detailed_activity:
        print("📋 DetailedActivity (from get_activity(id)):")
        print("   This is what you get when calling client.get_activity(activity_id)\n")
        
        if hasattr(detailed_activity, 'model_fields'):
            fields = detailed_activity.model_fields
        elif hasattr(detailed_activity, '__fields__'):
            fields = detailed_activity.__fields__
        else:
            fields = {}
        
        hr_fields = [f for f in fields.keys() if 'heart' in f.lower()]
        power_fields = [f for f in fields.keys() if 'power' in f.lower() or 'watt' in f.lower()]
        cadence_fields = [f for f in fields.keys() if 'cadence' in f.lower()]
        
        print(f"   Total fields: {len(fields)}")
        print(f"   Heart rate fields: {hr_fields if hr_fields else 'NONE ⚠️'}")
        print(f"   Power fields: {power_fields if power_fields else 'None'}")
        print(f"   Cadence fields: {cadence_fields if cadence_fields else 'None'}")
        
        # Show additional fields only in detailed
        if summary_activity:
            summary_fields = set(getattr(summary_activity, 'model_fields', getattr(summary_activity, '__fields__', {})).keys())
            detailed_fields = set(fields.keys())
            extra_fields = detailed_fields - summary_fields
            print(f"   Extra fields vs Summary: {sorted(extra_fields)}")
        print()
    
    if detailed_segment_effort:
        print("📋 DetailedSegmentEffort (in segment_efforts and best_efforts):")
        print("   Segment efforts within an activity contain per-segment metrics\n")
        
        if hasattr(detailed_segment_effort, 'model_fields'):
            fields = detailed_segment_effort.model_fields
        elif hasattr(detailed_segment_effort, '__fields__'):
            fields = detailed_segment_effort.__fields__
        else:
            fields = {}
        
        hr_fields = [f for f in fields.keys() if 'heart' in f.lower()]
        power_fields = [f for f in fields.keys() if 'power' in f.lower() or 'watt' in f.lower()]
        cadence_fields = [f for f in fields.keys() if 'cadence' in f.lower()]
        
        print(f"   Total fields: {len(fields)}")
        print(f"   Heart rate fields: {hr_fields if hr_fields else 'None'} ✓")
        print(f"   Power fields: {power_fields if power_fields else 'None'}")
        print(f"   Cadence fields: {cadence_fields if cadence_fields else 'None'}")
        print()
    
    if lap:
        print("📋 Lap (in laps array of DetailedActivity):")
        print("   Laps contain per-lap metrics\n")
        
        if hasattr(lap, 'model_fields'):
            fields = lap.model_fields
        elif hasattr(lap, '__fields__'):
            fields = lap.__fields__
        else:
            fields = {}
        
        hr_fields = [f for f in fields.keys() if 'heart' in f.lower()]
        power_fields = [f for f in fields.keys() if 'power' in f.lower() or 'watt' in f.lower()]
        cadence_fields = [f for f in fields.keys() if 'cadence' in f.lower()]
        
        print(f"   Total fields: {len(fields)}")
        print(f"   Heart rate fields: {hr_fields if hr_fields else 'None'}")
        print(f"   Power fields: {power_fields if power_fields else 'None'}")
        print(f"   Cadence fields: {cadence_fields if cadence_fields else 'None'}")
        print()
    
    print("🔍 KEY FINDINGS:")
    print("   • SummaryActivity (get_activities) does NOT have heart rate fields")
    print("   • DetailedActivity (get_activity) does NOT have activity-level HR fields")
    print("   • DetailedSegmentEffort HAS average_heartrate and max_heartrate")
    print("   • For activity-level HR data, you need to use:")
    print("     - Streams: client.get_activity_streams(id, types=['heartrate'])")
    print("     - Or check if there's an average in segment efforts")
    print()


def print_activity_summary(activity, index=None):
    """Print a summary of an activity"""
    prefix = f"Activity {index}: " if index is not None else "Activity: "
    print(f"{prefix}{activity.name}")
    print(f"  ID: {activity.id}")
    print(f"  Type: {activity.type}")
    print(f"  Date: {activity.start_date}")
    print(f"  Distance: {activity.distance}")
    print(f"  Duration: {activity.moving_time}")


def analyze_activity_fields(activity, detailed=False):
    """Analyze and display all available fields in an activity object"""
    activity_dict = dict(activity)
    
    label = "DETAILED ACTIVITY" if detailed else "SUMMARY ACTIVITY"
    print_section(f"{label} FIELDS - Activity ID: {activity.id}")
    
    # Get all fields
    all_fields = sorted(activity_dict.keys())
    
    # Categorize fields
    hr_fields = [f for f in all_fields if 'heart' in f.lower() or 'hr' in f.lower()]
    time_fields = [f for f in all_fields if 'time' in f.lower() or 'date' in f.lower()]
    distance_fields = [f for f in all_fields if 'distance' in f.lower() or 'meter' in f.lower()]
    pace_speed_fields = [f for f in all_fields if 'pace' in f.lower() or 'speed' in f.lower()]
    power_fields = [f for f in all_fields if 'power' in f.lower() or 'watt' in f.lower()]
    cadence_fields = [f for f in all_fields if 'cadence' in f.lower()]
    elevation_fields = [f for f in all_fields if 'elev' in f.lower() or 'altitude' in f.lower()]
    
    print(f"Total fields: {len(all_fields)}\n")
    
    # Print heart rate fields with values
    if hr_fields:
        print("❤️  HEART RATE FIELDS:")
        for field in hr_fields:
            value = activity_dict.get(field)
            print(f"  {field:30s} = {value}")
    else:
        print("❤️  HEART RATE FIELDS: None found")
    
    print()
    
    # Print power fields with values
    if power_fields:
        print("⚡ POWER FIELDS:")
        for field in power_fields:
            value = activity_dict.get(field)
            print(f"  {field:30s} = {value}")
    else:
        print("⚡ POWER FIELDS: None found")
    
    print()
    
    # Print cadence fields
    if cadence_fields:
        print("🔄 CADENCE FIELDS:")
        for field in cadence_fields:
            value = activity_dict.get(field)
            print(f"  {field:30s} = {value}")
    else:
        print("🔄 CADENCE FIELDS: None found")
    
    print()
    
    # Print selected important fields
    important_fields = [
        'name', 'type', 'distance', 'moving_time', 'elapsed_time',
        'total_elevation_gain', 'achievement_count', 'kudos_count',
        'average_speed', 'max_speed', 'calories'
    ]
    
    print("📊 KEY FIELDS:")
    for field in important_fields:
        if field in activity_dict:
            value = activity_dict.get(field)
            print(f"  {field:30s} = {value}")
    
    return activity_dict


def fetch_activity_streams(client, activity_id, verbose=False):
    """Fetch and display activity streams (time-series data)"""
    print_section(f"ACTIVITY STREAMS - Activity ID: {activity_id}")
    
    # Available stream types: time, distance, latlng, altitude, velocity_smooth,
    # heartrate, cadence, watts, temp, moving, grade_smooth
    stream_types = ['time', 'heartrate', 'cadence', 'watts', 'altitude', 'distance']
    
    try:
        streams = client.get_activity_streams(activity_id, types=stream_types)
        
        print(f"Available stream types: {list(streams.keys())}\n")
        
        for stream_type, stream in streams.items():
            print(f"📈 {stream_type.upper()} STREAM:")
            print(f"  Data points: {len(stream.data)}")
            print(f"  Series type: {stream.series_type}")
            print(f"  Original size: {stream.original_size}")
            print(f"  Resolution: {stream.resolution}")
            
            if verbose and stream.data:
                # Show first and last few data points
                data_preview = stream.data[:5] if len(stream.data) > 5 else stream.data
                print(f"  First values: {data_preview}")
                if len(stream.data) > 5:
                    print(f"  Last values: {stream.data[-5:]}")
                
                # Calculate stats for numeric streams
                if stream_type in ['heartrate', 'cadence', 'watts', 'altitude']:
                    numeric_data = [x for x in stream.data if x is not None]
                    if numeric_data:
                        print(f"  Min: {min(numeric_data)}")
                        print(f"  Max: {max(numeric_data)}")
                        print(f"  Avg: {sum(numeric_data) / len(numeric_data):.2f}")
            
            print()
        
        return streams
    
    except Exception as e:
        print(f"❌ Error fetching streams: {e}")
        return None


def analyze_segment_efforts_for_hr(activity, verbose=False):
    """Analyze segment efforts to find heart rate data"""
    print_section(f"SEGMENT EFFORTS HEART RATE - Activity ID: {activity.id}")
    
    activity_dict = dict(activity)
    segment_efforts = activity_dict.get('segment_efforts', [])
    
    if not segment_efforts:
        print("⚠️  No segment efforts found in this activity")
        print("   (Segments are only available for certain activities)")
        return None
    
    print(f"Found {len(segment_efforts)} segment efforts\n")
    
    hr_data = []
    for i, effort in enumerate(segment_efforts, 1):
        effort_dict = dict(effort)
        avg_hr = effort_dict.get('average_heartrate')
        max_hr = effort_dict.get('max_heartrate')
        segment_name = effort_dict.get('name', 'Unknown')
        
        if avg_hr or max_hr:
            hr_data.append({
                'name': segment_name,
                'avg_hr': avg_hr,
                'max_hr': max_hr
            })
            
            if verbose or i <= 3:  # Show first 3 or all if verbose
                print(f"Segment {i}: {segment_name}")
                print(f"  Average HR: {avg_hr if avg_hr else 'N/A'} bpm")
                print(f"  Max HR: {max_hr if max_hr else 'N/A'} bpm")
                print()
    
    if hr_data:
        # Calculate overall stats
        avg_hrs = [d['avg_hr'] for d in hr_data if d['avg_hr']]
        max_hrs = [d['max_hr'] for d in hr_data if d['max_hr']]
        
        print(f"📊 SUMMARY:")
        print(f"  Segments with HR data: {len(hr_data)} / {len(segment_efforts)}")
        if avg_hrs:
            print(f"  Average HR across segments: {sum(avg_hrs) / len(avg_hrs):.1f} bpm")
            print(f"  HR range: {min(avg_hrs):.0f} - {max(max_hrs):.0f} bpm")
    else:
        print("❌ No heart rate data found in segment efforts")
        print("   This could mean:")
        print("   • The activity wasn't recorded with a heart rate monitor")
        print("   • HR data is private/hidden in Strava settings")
    
    return hr_data


def compare_summary_vs_detailed(client, activity_id):
    """Compare summary vs detailed activity data"""
    print_section(f"COMPARISON: Summary vs Detailed - Activity ID: {activity_id}")
    
    # This requires fetching the activity twice - once we already have the summary
    # from get_activities(), now get detailed
    try:
        detailed = client.get_activity(activity_id)
        detailed_dict = dict(detailed)
        
        print("Fields only available in DETAILED view:")
        print("(Note: This shows fields that might have more data in detailed view)\n")
        
        # Show some key fields that are often richer in detailed view
        detail_fields = [
            'description', 'photos', 'gear', 'segment_efforts',
            'splits_metric', 'splits_standard', 'laps',
            'device_name', 'embed_token', 'calories'
        ]
        
        for field in detail_fields:
            if field in detailed_dict:
                value = detailed_dict[field]
                has_data = value is not None and (
                    (isinstance(value, (list, dict)) and len(value) > 0) or
                    (not isinstance(value, (list, dict)))
                )
                status = "✓ Has data" if has_data else "✗ Empty/None"
                print(f"  {field:30s} {status}")
                if has_data and field in ['device_name', 'calories', 'gear']:
                    print(f"    → {value}")
        
        return detailed
    
    except Exception as e:
        print(f"❌ Error fetching detailed activity: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Explore stravalib models and data availability',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--athlete-id', type=int,
                        help='Your Strava athlete ID (not required for --show-models)')
    parser.add_argument('--limit', type=int, default=5,
                        help='Number of activities to analyze (default: 5)')
    parser.add_argument('--detailed', action='store_true',
                        help='Fetch detailed activity data')
    parser.add_argument('--streams', action='store_true',
                        help='Fetch activity streams (time-series data)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--activity-id', type=int,
                        help='Analyze a specific activity by ID')
    parser.add_argument('--show-models', action='store_true',
                        help='Show stravalib model definitions and exit')
    
    args = parser.parse_args()
    
    # If just showing models, do that and exit
    if args.show_models:
        inspect_model_definitions()
        return 0
    
    # Otherwise, require athlete ID
    if not args.athlete_id:
        parser.error('--athlete-id is required (unless using --show-models)')
    
    print_section("STRAVALIB MODEL EXPLORER")
    print(f"Athlete ID: {args.athlete_id}")
    print(f"Limit: {args.limit}")
    print(f"Detailed: {args.detailed}")
    print(f"Streams: {args.streams}")
    print(f"Verbose: {args.verbose}")
    
    # Get athlete from database
    print("\n🔍 Fetching athlete data from database...")
    athlete = db.get_athlete_by_id(args.athlete_id)
    
    if not athlete:
        print(f"❌ Error: Athlete with ID {args.athlete_id} not found in database")
        print("   Make sure you've logged in at least once through the app")
        return 1
    
    print(f"✓ Found athlete: {athlete['firstname']} {athlete['lastname']}")
    print(f"  Token expires: {athlete['expires_at']}")
    
    # Get valid Strava client (will refresh token if needed)
    print("\n🔑 Getting Strava API client...")
    client = h.get_valid_strava_client(athlete, CLIENT_ID, CLIENT_SECRET)
    print("✓ Client authenticated")
    
    # Show model definitions first
    if args.verbose:
        inspect_model_definitions()
    
    if args.activity_id:
        # Analyze specific activity
        print(f"\n📊 Analyzing activity {args.activity_id}...")
        try:
            activity = client.get_activity(args.activity_id)
            print_activity_summary(activity)
            analyze_activity_fields(activity, detailed=True)
            
            # Check segment efforts for HR
            analyze_segment_efforts_for_hr(activity, verbose=args.verbose)
            
            if args.streams:
                fetch_activity_streams(client, args.activity_id, verbose=args.verbose)
        except Exception as e:
            print(f"❌ Error fetching activity: {e}")
            return 1
    else:
        # Fetch recent activities
        print(f"\n📅 Fetching last {args.limit} activities...")
        
        # Get activities from last 90 days
        after = datetime.now() - timedelta(days=90)
        activities = list(client.get_activities(after=after, limit=args.limit))
        
        print(f"✓ Found {len(activities)} activities\n")
        
        if not activities:
            print("❌ No activities found in the last 90 days")
            return 1
        
        # Analyze first activity in detail
        print_section("ANALYZING FIRST ACTIVITY")
        first_activity = activities[0]
        print_activity_summary(first_activity)
        
        # Show summary fields
        print("\n" + "─" * 80)
        print("SUMMARY ACTIVITY DATA:")
        print("─" * 80)
        analyze_activity_fields(first_activity, detailed=False)
        
        # Show detailed fields if requested
        if args.detailed:
            print("\n" + "─" * 80)
            print("FETCHING DETAILED ACTIVITY DATA:")
            print("─" * 80)
            detailed_activity = compare_summary_vs_detailed(client, first_activity.id)
            if detailed_activity:
                analyze_activity_fields(detailed_activity, detailed=True)
                # Analyze segment efforts for heart rate
                analyze_segment_efforts_for_hr(detailed_activity, verbose=args.verbose)
        
        # Show streams if requested
        if args.streams:
            fetch_activity_streams(client, first_activity.id, verbose=args.verbose)
        
        # List other activities
        if len(activities) > 1:
            print_section(f"OTHER ACTIVITIES (showing {len(activities) - 1} more)")
            for i, activity in enumerate(activities[1:], start=2):
                print_activity_summary(activity, index=i)
                print()
    
    print_section("SUMMARY & RECOMMENDATIONS")
    print("✓ Analysis complete!")
    print("\n🔍 Key takeaways:")
    print("  • SummaryActivity (get_activities) does NOT have HR fields")
    print("  • DetailedActivity (get_activity) does NOT have activity-level HR fields")
    print("  • Heart rate data IS available in:")
    print("    ✓ DetailedSegmentEffort.average_heartrate")
    print("    ✓ DetailedSegmentEffort.max_heartrate")
    print("    ✓ Activity Streams (get_activity_streams)")
    print()
    print("💡 Recommendations for getting HR data:")
    print("  1. Use streams for time-series HR data:")
    print("     streams = client.get_activity_streams(id, types=['heartrate'])")
    print("  2. Use segment efforts for average/max HR:")
    print("     activity = client.get_activity(id)")
    print("     for effort in activity.segment_efforts:")
    print("         print(effort.average_heartrate)")
    print()
    print("📚 To see model definitions:")
    print("  python tests/stravalibmodels.py --show-models")
    print()
    print("🔗 Reference files in your venv:")
    print("  venv/lib/python3.11/site-packages/stravalib/strava_model.py")
    print("  venv/lib/python3.11/site-packages/stravalib/model.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

