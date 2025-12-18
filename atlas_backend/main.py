import sys
from optimized_pipeline import OptimizedResearchAgent as AutonomousLeadAgent
from report_generator import generate_report

def main():
    print("==========================================")
    print("   ATLAS: AUTONOMOUS INTELLIGENCE AGENT   ")
    print("==========================================")
    
    if len(sys.argv) > 1:
        company = sys.argv[1]
    else:
        company = input("Enter Company Name/Domain to Research: ")

    if not company:
        print("❌ No company provided.")
        return

    # Execute the new pipeline
    # The agent now returns a CompanyProfile object
    agent = AutonomousLeadAgent(company)
    company_profile = agent.run_pipeline()

    # Generate Report (JSON + PDF)
    generate_report(company_profile)

if __name__ == "__main__":
    main()