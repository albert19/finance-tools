<?php
namespace App\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'investments')]
#[ORM\Index(name: 'idx_investment_user', columns: ['user_id'])]
class Investment
{
    #[ORM\Id, ORM\Column(type: 'string', length: 36, options: ['fixed' => true])]
    public string $id;
    #[ORM\ManyToOne(targetEntity: User::class), ORM\JoinColumn(name: 'user_id', nullable: false, onDelete: 'CASCADE')]
    public User $owner;
    #[ORM\Column(length: 150)]
    public string $name;
    #[ORM\Column(name: 'start_date', type: 'date_immutable')]
    public \DateTimeImmutable $startDate;
    #[ORM\Column(length: 10, options: ['default' => 'active'])]
    public string $status = 'active';
    #[ORM\Column(type: 'text', length: 65535)]
    public string $notes = '';
    #[ORM\Column(type: 'json')]
    public array $parameters;

    public function __construct(string $id, User $owner, string $name, string $startDate, string $notes, array $parameters)
    {
        $this->id = $id;
        $this->owner = $owner;
        $this->name = $name;
        $this->startDate = new \DateTimeImmutable($startDate);
        $this->notes = $notes;
        $this->parameters = $parameters;
    }

    public function addSnapshot(string $id, string $date, string $marketValue, string $contribution, string $withdrawal, string $note): InvestmentSnapshot
    {
        if ($date < $this->startDate->format('Y-m-d')) {
            throw new \DomainException('Snapshot date must be on or after investment start');
        }
        return new InvestmentSnapshot($id, $this, $date, $marketValue, $contribution, $withdrawal, $note);
    }
}
