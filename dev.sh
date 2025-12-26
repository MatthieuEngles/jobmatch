#!/bin/bash
# dev.sh - Interactive development script for JobMatch
# Usage: ./dev.sh

# Don't exit on error - handle gracefully
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Available services (some may not be implemented yet)
SERVICES=("gui" "cv-ingestion" "ai-assistant" "db" "redis")
# Core services that are always needed
CORE_SERVICES="db gui"

print_header() {
    clear
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                    JobMatch Dev Tools                     ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_status() {
    echo -e "\n${BLUE}📊 Current Status:${NC}"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "Docker Compose not running"
    echo ""
}

select_service() {
    echo -e "${YELLOW}Select a service:${NC}"
    select service in "${SERVICES[@]}" "Cancel"; do
        if [[ "$service" == "Cancel" ]]; then
            return 1
        elif [[ -n "$service" ]]; then
            echo "$service"
            return 0
        fi
    done
}

menu_start() {
    echo -e "${YELLOW}Start options:${NC}"
    echo "1) Start core services only (db, gui)"
    echo "2) Start all available services"
    echo "3) Cancel"
    read -p "Choice: " choice

    case $choice in
        1)
            echo -e "${GREEN}▶ Starting core services (db, gui)...${NC}"
            docker-compose up -d db
            sleep 3
            docker-compose up -d gui
            echo -e "${GREEN}✓ Core services started${NC}"
            ;;
        2)
            echo -e "${GREEN}▶ Starting all services...${NC}"
            # Start services one by one, ignore errors for missing ones
            for svc in db redis gui cv-ingestion ai-assistant; do
                echo -e "${BLUE}Starting $svc...${NC}"
                docker-compose up -d "$svc" 2>/dev/null || echo -e "${YELLOW}⚠ $svc not available (skipped)${NC}"
            done
            echo -e "${GREEN}✓ Available services started${NC}"
            ;;
    esac
}

menu_stop() {
    echo -e "${YELLOW}⏹ Stopping all services (data preserved)...${NC}"
    docker-compose down
    echo -e "${GREEN}✓ Services stopped. Data is preserved in volumes.${NC}"
}

menu_rebuild() {
    echo -e "${YELLOW}🔨 Rebuild a service${NC}"
    service=$(select_service)
    if [[ $? -eq 0 ]]; then
        echo -e "${BLUE}Rebuilding $service...${NC}"
        if docker-compose up -d --build "$service" 2>&1; then
            echo -e "${GREEN}✓ $service rebuilt and restarted${NC}"
        else
            echo -e "${RED}✗ Failed to rebuild $service (service may not be implemented yet)${NC}"
        fi
    fi
}

menu_logs() {
    echo -e "${YELLOW}📜 View logs${NC}"
    service=$(select_service)
    if [[ $? -eq 0 ]]; then
        echo -e "${BLUE}Showing logs for $service (Ctrl+C to exit)...${NC}"
        docker-compose logs -f "$service"
    fi
}

menu_shell() {
    echo -e "${YELLOW}🐚 Open a shell${NC}"
    echo "1) Django shell (Python)"
    echo "2) Bash shell in container"
    echo "3) PostgreSQL shell"
    echo "4) Cancel"
    read -p "Choice: " choice

    case $choice in
        1)
            echo -e "${BLUE}Opening Django shell...${NC}"
            docker-compose exec gui python manage.py shell
            ;;
        2)
            service=$(select_service)
            if [[ $? -eq 0 ]]; then
                docker-compose exec "$service" /bin/sh
            fi
            ;;
        3)
            echo -e "${BLUE}Opening PostgreSQL shell...${NC}"
            docker-compose exec db psql -U jobmatch -d jobmatch
            ;;
    esac
}

menu_migrate() {
    echo -e "${YELLOW}🗄️ Database migrations${NC}"
    echo "1) Apply migrations (migrate)"
    echo "2) Create migrations (makemigrations)"
    echo "3) Show migration status"
    echo "4) Cancel"
    read -p "Choice: " choice

    case $choice in
        1)
            echo -e "${BLUE}Applying migrations...${NC}"
            docker-compose exec -T gui python manage.py migrate
            echo -e "${GREEN}✓ Migrations applied${NC}"
            ;;
        2)
            read -p "App name (leave empty for all): " app
            echo -e "${BLUE}Creating migrations...${NC}"
            docker-compose exec -T gui python manage.py makemigrations $app
            echo -e "${GREEN}✓ Migrations created${NC}"
            ;;
        3)
            docker-compose exec -T gui python manage.py showmigrations
            ;;
    esac
}

menu_create_superuser() {
    echo -e "${YELLOW}👤 Create superuser${NC}"
    docker-compose exec gui python manage.py createsuperuser
}

menu_reset_db() {
    echo -e "${RED}⚠️  WARNING: This will DELETE ALL DATA!${NC}"
    echo -e "${RED}Are you absolutely sure? Type 'DELETE' to confirm:${NC}"
    read -p "> " confirm

    if [[ "$confirm" == "DELETE" ]]; then
        echo -e "${RED}Destroying database...${NC}"
        docker-compose down -v
        sleep 2
        echo -e "${BLUE}Recreating services...${NC}"
        docker-compose up -d
        sleep 5
        echo -e "${BLUE}Applying migrations...${NC}"
        docker-compose exec -T gui python manage.py migrate
        echo -e "${GREEN}✓ Database reset complete${NC}"
    else
        echo -e "${YELLOW}Cancelled.${NC}"
    fi
}

menu_quick_actions() {
    echo -e "${YELLOW}⚡ Quick Actions${NC}"
    echo "1) Restart GUI only (after code change)"
    echo "2) Restart AI Assistant only"
    echo "3) View GUI logs"
    echo "4) Run Django collectstatic"
    echo "5) Cancel"
    read -p "Choice: " choice

    case $choice in
        1)
            docker-compose restart gui
            echo -e "${GREEN}✓ GUI restarted${NC}"
            ;;
        2)
            docker-compose restart ai-assistant
            echo -e "${GREEN}✓ AI Assistant restarted${NC}"
            ;;
        3)
            docker-compose logs -f --tail=50 gui
            ;;
        4)
            docker-compose exec -T gui python manage.py collectstatic --noinput
            echo -e "${GREEN}✓ Static files collected${NC}"
            ;;
    esac
}

# Main menu loop
main() {
    while true; do
        print_header
        print_status

        echo -e "${CYAN}Main Menu:${NC}"
        echo "  1) 🚀 Start all services"
        echo "  2) ⏹  Stop all services"
        echo "  3) 🔨 Rebuild a service"
        echo "  4) 📜 View logs"
        echo "  5) 🐚 Open shell"
        echo "  6) 🗄️  Database migrations"
        echo "  7) 👤 Create superuser"
        echo "  8) ⚡ Quick actions"
        echo "  9) 💀 Reset database (DANGER)"
        echo "  0) 🚪 Exit"
        echo ""
        read -p "Choice [0-9]: " choice

        case $choice in
            1) menu_start ;;
            2) menu_stop ;;
            3) menu_rebuild ;;
            4) menu_logs ;;
            5) menu_shell ;;
            6) menu_migrate ;;
            7) menu_create_superuser ;;
            8) menu_quick_actions ;;
            9) menu_reset_db ;;
            0)
                echo -e "${GREEN}Bye! 👋${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice${NC}"
                ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
    done
}

# Check for command line arguments for quick actions
if [[ $# -gt 0 ]]; then
    case "$1" in
        start)
            echo -e "${GREEN}▶ Starting core services...${NC}"
            docker-compose up -d db && sleep 2 && docker-compose up -d gui
            echo -e "${GREEN}✓ Done${NC}"
            exit 0
            ;;
        stop)
            docker-compose down
            exit 0
            ;;
        restart)
            docker-compose restart "${2:-gui}"
            exit 0
            ;;
        full-restart)
            svc="${2:-gui}"
            echo -e "${YELLOW}Full restart of $svc (down + build + up)...${NC}"
            docker-compose stop "$svc"
            docker-compose rm -f "$svc"
            docker-compose up -d --build "$svc"
            echo -e "${GREEN}✓ $svc fully restarted${NC}"
            exit 0
            ;;
        rebuild)
            docker-compose up -d --build "${2:-gui}"
            exit 0
            ;;
        logs)
            docker-compose logs -f "${2:-gui}"
            exit 0
            ;;
        migrate)
            docker-compose exec -T gui python manage.py migrate
            exit 0
            ;;
        shell)
            docker-compose exec gui python manage.py shell
            exit 0
            ;;
        *)
            echo "Quick commands:"
            echo "  start                - Start core services (db + gui)"
            echo "  stop                 - Stop all services"
            echo "  restart [svc]        - Restart a service (default: gui)"
            echo "  full-restart [svc]   - Stop + rebuild + start a service"
            echo "  rebuild [svc]        - Rebuild and start a service"
            echo "  logs [svc]           - View logs for a service"
            echo "  migrate              - Apply Django migrations"
            echo "  shell                - Open Django shell"
            echo ""
            echo "Or run without arguments for interactive menu"
            exit 1
            ;;
    esac
fi

# Run interactive menu
main
