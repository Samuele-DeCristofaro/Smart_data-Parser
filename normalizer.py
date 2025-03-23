import os
import csv
import json
import logging
import argparse
from datetime import datetime
from tabulate import tabulate

class DiskHealthMonitor:
    def __init__(self, json_dir="disk_exs", output_file="report.csv", log_file="error_log.txt"):
        """Initialize the disk health monitor."""
        self.json_dir = json_dir
        self.output_file = output_file
        self.log_file = log_file
        self.setup_logging()
        
    def setup_logging(self):
        """Configure logging for the application."""
        logging.basicConfig(
            filename=self.log_file, 
            level=logging.ERROR,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        
    def load_json_data(self):
        """Load all JSON files from the specified directory."""
        json_data = []
        if not os.path.exists(self.json_dir):
            logging.error(f"Directory {self.json_dir} not found.")
            return json_data
            
        for filename in os.listdir(self.json_dir):
            if filename.endswith(".json"):
                file_path = os.path.join(self.json_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        json_data.append(json.load(f))
                except Exception as err:
                    logging.error(f"Error reading JSON file {file_path}: {err}")
        
        return json_data
    
    def extract_ata_data(self, data, index):
        """Extract relevant data from an ATA device."""
        p_on_h = data["power_on_time"].get("hours", "N/A")
        current_temp = data["temperature"].get("current", "N/A")
        reallocated_sectors = "N/A"
        
        for sect in data["ata_smart_attributes"]["table"]:
            if sect["name"] == "Reallocated_Sector_Ct":
                reallocated_sectors = sect["value"]
                break
        
        return [index, "ATA", p_on_h, current_temp, reallocated_sectors]
    
    def extract_nvme_data(self, data, index):
        """Extract relevant data from an NVMe device."""
        health_info = data["nvme_smart_health_information"]
        p_on_h = health_info.get("power_on_hours", "N/A")
        current_temp = health_info.get("temperature", "N/A")
        
        return [index, "NVMe", p_on_h, current_temp, "N/A"]
    
    def analyze_data(self, json_data):
        """Analyze disk data and categorize by type."""
        ata_data = []
        nvme_data = []
        all_data = []
        
        for idx, data in enumerate(json_data, start=1):
            if "ata_smart_attributes" in data:
                disk_data = self.extract_ata_data(data, idx)
                ata_data.append(disk_data[1:])  # Remove index for display
                all_data.append(disk_data)
            elif "nvme_smart_health_information" in data:
                disk_data = self.extract_nvme_data(data, idx)
                nvme_data.append(disk_data[1:])  # Remove index for display
                all_data.append(disk_data)
        
        return {
            "ata": ata_data,
            "nvme": nvme_data,
            "all": all_data
        }
    
    def display_report(self, analyzed_data):
        """Display a table with the analyzed data."""
        print("\n### ATA DEVICES ###")
        if analyzed_data["ata"]:
            print(tabulate(
                analyzed_data["ata"], 
                headers=["Type", "Power-on Hours", "Temperature", "Reallocated Sectors"], 
                tablefmt="grid"
            ))
        else:
            print("No ATA devices found.")
            
        print("\n### NVMe DEVICES ###")
        if analyzed_data["nvme"]:
            print(tabulate(
                analyzed_data["nvme"], 
                headers=["Type", "Power-on Hours", "Temperature"], 
                tablefmt="grid"
            ))
        else:
            print("No NVMe devices found.")
    
    def save_report(self, analyzed_data):
        """Save the analyzed data to a CSV file."""
        with open(self.output_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["# Device", "Type", "Power-on Hours", "Temperature", "Reallocated Sectors"])
            
            for row in analyzed_data["all"]:
                writer.writerow(row)
        
        print(f"Report saved to {self.output_file}!")
    
    def generate_html_report(self, analyzed_data, html_file="report.html"):
        """Generate a more detailed HTML report."""
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Disk Status Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .warning {{ background-color: #fff3cd; }}
        .danger {{ background-color: #f8d7da; }}
        .footer {{ margin-top: 30px; font-size: 0.8em; color: #666; }}
    </style>
</head>
<body>
    <h1>Disk Status Report</h1>
    <p>Generated on {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    
    <h2>ATA Devices</h2>
    {"<p>No ATA devices found.</p>" if not analyzed_data["ata"] else self._generate_html_table(analyzed_data["ata"], ["Type", "Power-on Hours", "Temperature", "Reallocated Sectors"])}
    
    <h2>NVMe Devices</h2>
    {"<p>No NVMe devices found.</p>" if not analyzed_data["nvme"] else self._generate_html_table(analyzed_data["nvme"], ["Type", "Power-on Hours", "Temperature"])}
    
    <div class="footer">
        <p>Report generated by DiskHealthMonitor</p>
    </div>
</body>
</html>"""
        
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"HTML report saved to {html_file}!")
    
    def _generate_html_table(self, data, headers):
        """Generate an HTML table from the provided data."""
        table = '<table>\n<tr>'
        
        # Table header
        for header in headers:
            table += f'<th>{header}</th>'
        table += '</tr>\n'
        
        # Table data
        for row in data:
            table += '<tr>'
            for i, cell in enumerate(row):
                if i >= len(headers):
                    # Skip cells that don't have corresponding headers
                    continue
                    
                cell_str = str(cell)  # Convert value to string for safe comparison
                
                # Add warning class if reallocated sectors > 0
                if i == 3 and i < len(headers) and headers[i] == "Reallocated Sectors" and cell_str != "N/A" and cell_str != "0":
                    try:
                        if int(cell_str) > 0:
                            table += f'<td class="warning">{cell_str}</td>'
                        else:
                            table += f'<td>{cell_str}</td>'
                    except ValueError:
                        table += f'<td>{cell_str}</td>'
                        
                # Add warning class if power-on hours are high
                elif i == 1 and i < len(headers) and headers[i] == "Power-on Hours" and cell_str != "N/A":
                    try:
                        if int(cell_str) > 30000:
                            table += f'<td class="warning">{cell_str}</td>'
                        else:
                            table += f'<td>{cell_str}</td>'
                    except ValueError:
                        table += f'<td>{cell_str}</td>'
                        
                # Add danger class if temperature is high
                elif i == 2 and i < len(headers) and headers[i] == "Temperature" and cell_str != "N/A":
                    try:
                        if int(cell_str) > 50:
                            table += f'<td class="danger">{cell_str}</td>'
                        else:
                            table += f'<td>{cell_str}</td>'
                    except ValueError:
                        table += f'<td>{cell_str}</td>'
                else:
                    table += f'<td>{cell_str}</td>'
            table += '</tr>\n'
        
        table += '</table>'
        return table
    
    def run(self):
        """Run the complete analysis and generate reports."""
        json_data = self.load_json_data()
        if not json_data:
            print("No data found. Verify the JSON files directory.")
            return False
        
        analyzed_data = self.analyze_data(json_data)
        self.display_report(analyzed_data)
        self.save_report(analyzed_data)
        self.generate_html_report(analyzed_data)
        return True


def main():
    """Main function that initializes and starts the monitor."""
    parser = argparse.ArgumentParser(description="SMART disk health monitor.")
    parser.add_argument("-d", "--directory", default="disk_exs", help="Directory containing SMART JSON files")
    parser.add_argument("-o", "--output", default="report.csv", help="Output CSV filename")
    parser.add_argument("--html", action="store_true", help="Also generate an HTML report")
    parser.add_argument("--log", default="error_log.txt", help="Error log file")
    
    args = parser.parse_args()
    
    monitor = DiskHealthMonitor(args.directory, args.output, args.log)
    monitor.run()


if __name__ == "__main__":
    main()